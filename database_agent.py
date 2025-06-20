"""
Conversational Database Agent for MongoDB
Implements natural language to MongoDB query translation with conversation memory
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re

import pymongo
from pymongo import MongoClient
from bson import ObjectId
import openai
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from config import config, SAMPLE_ANALYTICS_SCHEMA, QUERY_TYPES, SAMPLE_QUERIES


logging.basicConfig(level=logging.INFO if config.agent.debug_mode else logging.WARNING)
logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Result of a database query"""
    success: bool
    data: Any
    count: int
    query_type: str
    execution_time_ms: float
    error_message: Optional[str] = None

@dataclass
class ConversationInsight:
    """Insights extracted from conversation"""
    user_intent: str
    emotional_tone: str
    data_gaps: List[str]
    suggested_queries: List[str]

class DatabaseSchemaManager:
    """Manages MongoDB schema metadata and field mappings"""

    def __init__(self, client: MongoClient, database_name: str):
        self.client = client
        self.database_name = database_name
        self.db = client[database_name]
        self.schema_cache = {}

    def discover_schema(self) -> Dict[str, Any]:
        """Discover database schema by examining collections and documents"""
        schema = {}

        try:
            collections = self.db.list_collection_names()
            logger.info(f"Found collections: {collections}")

            for collection_name in collections:
                collection = self.db[collection_name]

                #//
                sample_docs = list(collection.find().limit(5))
                if not sample_docs:
                    continue

                #field infoo
                fields = {}
                for doc in sample_docs:
                    for field, value in doc.items():
                        if field not in fields:
                            fields[field] = {
                                "type": type(value).__name__,
                                "sample_value": str(value)[:100]
                            }

                schema[collection_name] = {
                    "document_count": collection.count_documents({}),
                    "fields": fields,
                    "indexes": list(collection.list_indexes())
                }

        except Exception as e:
            logger.error(f"Error discovering schema: {e}")

        self.schema_cache = schema
        return schema
    #  using SAMPLE ANALYTICS data because of the limited time as well as I had a lot of things to learn already, so this would have taken much longer. If you want me to do it with other data, reach out to me again.
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific collection"""
        if collection_name in SAMPLE_ANALYTICS_SCHEMA:
            return SAMPLE_ANALYTICS_SCHEMA[collection_name]

        if collection_name in self.schema_cache:
            return self.schema_cache[collection_name]

        return {}

class NaturalLanguageProcessor:
    """Processes natural language queries using OpenAI GPT (smart)"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=config.llm.api_key)

    def classify_query(self, query: str, schema_info: Dict) -> Dict[str, Any]:
        """Classify user query and extract intent"""

        system_prompt = f"""You are an expert at analyzing natural language queries for MongoDB databases.

Database Schema:
{json.dumps(schema_info, indent=2)}

Query Types:
{json.dumps(QUERY_TYPES, indent=2)}

Sample Queries:
{json.dumps(SAMPLE_QUERIES, indent=2)}

Classify the user query and return a JSON response with:
1. query_type: one of {list(QUERY_TYPES.keys())}
2. collection: which collection to query
3. intent: detailed description of what user wants
4. confidence: confidence score (0-1)
5. extracted_fields: relevant fields mentioned
6. filters: any filtering criteria mentioned
7. aggregation_type: if aggregation, specify type (sum, avg, count, etc.)

Be precise and consider context from the schema."""

        try:
            response = self.client.chat.completions.create(
                model=config.llm.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                temperature=config.llm.temperature,
                max_tokens=500
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            return {
                "query_type": "unknown",
                "collection": "unknown", 
                "intent": query,
                "confidence": 0.0,
                "extracted_fields": [],
                "filters": {},
                "aggregation_type": None
            }

class MongoDBQueryExecutor:
    """Translates intents to MongoDB queries and executes them"""

    def __init__(self, client: MongoClient, database_name: str):
        self.client = client
        self.database_name = database_name
        self.db = client[database_name]
        self.nlp = NaturalLanguageProcessor()

    def translate_to_mongodb_query(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Translate classified intent to MongoDB query"""

        query_type = classification.get("query_type")
        collection = classification.get("collection")

        if query_type == "definition":
            return {"type": "definition", "collection": collection}

        elif query_type == "filter":
            return {
                "type": "find",
                "collection": collection,
                "filter": classification.get("filters", {}),
                "limit": config.agent.max_query_results
            }

        elif query_type == "count":
            return {
                "type": "count",
                "collection": collection,
                "filter": classification.get("filters", {})
            }

        elif query_type == "aggregation":
            agg_type = classification.get("aggregation_type", "count")
            field = classification.get("extracted_fields", [None])[0]

            pipeline = []
            if classification.get("filters"):
                pipeline.append({"$match": classification["filters"]})

            if agg_type == "avg" and field:
                pipeline.append({"$group": {"_id": None, "result": {"$avg": f"${field}"}}})
            elif agg_type == "sum" and field:
                pipeline.append({"$group": {"_id": None, "result": {"$sum": f"${field}"}}})
            elif agg_type == "max" and field:
                pipeline.append({"$group": {"_id": None, "result": {"$max": f"${field}"}}})
            elif agg_type == "min" and field:
                pipeline.append({"$group": {"_id": None, "result": {"$min": f"${field}"}}})
            else:
                pipeline.append({"$group": {"_id": None, "count": {"$sum": 1}}})

            return {
                "type": "aggregate",
                "collection": collection,
                "pipeline": pipeline
            }

        elif query_type == "trend":
            # Time-based analysis
            date_field = self._find_date_field(collection)
            pipeline = [
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m", "date": f"${date_field}"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]

            return {
                "type": "aggregate",
                "collection": collection,
                "pipeline": pipeline
            }

        return {"type": "unknown"}

    def _find_date_field(self, collection_name: str) -> str:
        """Find the most likely date field in a collection"""
        date_fields = ["date", "created_at", "timestamp", "birthdate", 
                      "bucket_start_date", "bucket_end_date"]

        if collection_name in SAMPLE_ANALYTICS_SCHEMA:
            fields = SAMPLE_ANALYTICS_SCHEMA[collection_name]["fields"]
            for field in date_fields:
                if field in fields:
                    return field

        return "created_at"  # Default fallback

    def execute_query(self, query_dict: Dict[str, Any]) -> QueryResult:
        """Execute MongoDB query and return results"""
        start_time = datetime.now()

        try:
            query_type = query_dict.get("type")
            collection_name = query_dict.get("collection")

            if query_type == "definition":
                return self._handle_definition(collection_name, start_time)

            if not collection_name or collection_name not in self.db.list_collection_names():
                return QueryResult(
                    success=False,
                    data=None,
                    count=0,
                    query_type=query_type,
                    execution_time_ms=0,
                    error_message=f"Collection '{collection_name}' not found"
                )

            collection = self.db[collection_name]

            if query_type == "find":
                filter_dict = query_dict.get("filter", {})
                limit = query_dict.get("limit", config.agent.max_query_results)

                cursor = collection.find(filter_dict).limit(limit)
                results = list(cursor)

                return QueryResult(
                    success=True,
                    data=results,
                    count=len(results),
                    query_type=query_type,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            elif query_type == "count":
                filter_dict = query_dict.get("filter", {})
                count = collection.count_documents(filter_dict)

                return QueryResult(
                    success=True,
                    data={"count": count},
                    count=count,
                    query_type=query_type,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            elif query_type == "aggregate":
                pipeline = query_dict.get("pipeline", [])
                results = list(collection.aggregate(pipeline))

                return QueryResult(
                    success=True,
                    data=results,
                    count=len(results),
                    query_type=query_type,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return QueryResult(
                success=False,
                data=None,
                count=0,
                query_type=query_dict.get("type", "unknown"),
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=str(e)
            )

    def _handle_definition(self, collection_name: str, start_time: datetime) -> QueryResult:
        """Handle definition queries"""
        if collection_name in SAMPLE_ANALYTICS_SCHEMA:
            info = SAMPLE_ANALYTICS_SCHEMA[collection_name]

            return QueryResult(
                success=True,
                data={
                    "definition": info["description"],
                    "fields": info["fields"],
                    "relationships": info.get("relationships", {})
                },
                count=1,
                query_type="definition",
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        return QueryResult(
            success=False,
            data=None,
            count=0,
            query_type="definition",
            execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            error_message=f"No definition available for collection '{collection_name}'"
        )

class ConversationMemoryManager:
    """Manages conversation history and context using LangChain"""

    def __init__(self):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="human_input",
            output_key="ai_output",
            return_messages=True
        )
        self.conversation_log = []

    def add_exchange(self, human_input: str, ai_output: str, query_result: Optional[QueryResult] = None):
        """Add a conversation exchange to memory"""
        self.memory.save_context(
            {"human_input": human_input},
            {"ai_output": ai_output}
        )

        exchange = {
            "timestamp": datetime.now().isoformat(),
            "human_input": human_input,
            "ai_output": ai_output,
            "query_result": query_result.__dict__ if query_result else None
        }

        self.conversation_log.append(exchange)

        # Limit conversation history
        if len(self.conversation_log) > config.agent.max_conversation_history:
            self.conversation_log = self.conversation_log[-config.agent.max_conversation_history:]

    def get_conversation_context(self) -> str:
        """Get formatted conversation history for context"""
        messages = self.memory.chat_memory.messages

        context = []
        for message in messages[-10:]:  # Last 10 messages
            if isinstance(message, HumanMessage):
                context.append(f"Human: {message.content}")
            elif isinstance(message, AIMessage):
                context.append(f"Assistant: {message.content}")

        return "\n".join(context)

    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        self.conversation_log = []

class InsightExtractor:
    """Extracts actionable insights from conversations and data gaps"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=config.llm.api_key)

    def extract_insights(self, conversation_log: List[Dict], query_results: List[QueryResult]) -> ConversationInsight:
        """Extract insights from conversation and query results"""

        # Analyze conversation for insights
        conversation_text = "\n".join([
            f"User: {exchange['human_input']}\nAssistant: {exchange['ai_output']}"
            for exchange in conversation_log[-5:]  # Last 5 exchanges
        ])

        prompt = f"""Analyze this conversation and extract insights:

Conversation:
{conversation_text}

Extract:
1. User Intent: What is the user ultimately trying to accomplish?
2. Emotional Tone: What is the user's emotional state? (curious, frustrated, satisfied, etc.)
3. Data Gaps: What data or insights is the user missing?
4. Suggested Queries: What follow-up questions might be helpful?

Return as JSON with keys: user_intent, emotional_tone, data_gaps (array), suggested_queries (array)"""

        try:
            response = self.client.chat.completions.create(
                model=config.llm.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            result = json.loads(response.choices[0].message.content)

            return ConversationInsight(
                user_intent=result.get("user_intent", "Unknown"),
                emotional_tone=result.get("emotional_tone", "Neutral"),
                data_gaps=result.get("data_gaps", []),
                suggested_queries=result.get("suggested_queries", [])
            )

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return ConversationInsight(
                user_intent="Unknown",
                emotional_tone="Neutral", 
                data_gaps=[],
                suggested_queries=[]
            )

class ConversationalDatabaseAgent:
    """Main orchestrator for the conversational database agent"""

    def __init__(self):
        self.client = None
        self.schema_manager = None
        self.query_executor = None
        self.memory_manager = ConversationMemoryManager()
        self.insight_extractor = InsightExtractor()
        self.nlp = NaturalLanguageProcessor()

    def connect_database(self) -> bool:
        """Connect to MongoDB database"""
        try:
            self.client = MongoClient(
                config.database.connection_string,
                serverSelectionTimeoutMS=config.database.timeout_ms,
                maxPoolSize=config.database.max_pool_size
            )

            # Test connection
            self.client.admin.command('ping')

            self.schema_manager = DatabaseSchemaManager(self.client, config.database.database_name)
            self.query_executor = MongoDBQueryExecutor(self.client, config.database.database_name)

            logger.info(f"✅ Connected to MongoDB: {config.database.database_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    def process_query(self, user_input: str) -> Tuple[str, QueryResult]:
        """Process a natural language query and return response"""

        # Get conversation context
        context = self.memory_manager.get_conversation_context()

        # Discover schema if not cached
        if not self.schema_manager.schema_cache:
            self.schema_manager.discover_schema()

        # Classify the query
        classification = self.nlp.classify_query(
            user_input, 
            self.schema_manager.schema_cache
        )

        logger.info(f"Query classification: {classification}")

        # Translate to MongoDB query
        query_dict = self.query_executor.translate_to_mongodb_query(classification)

        # Execute query
        query_result = self.query_executor.execute_query(query_dict)

        # Generate natural language response
        response = self._generate_response(user_input, classification, query_result, context)

        # Add to conversation memory
        self.memory_manager.add_exchange(user_input, response, query_result)

        return response, query_result

    def _generate_response(self, user_input: str, classification: Dict, 
                          query_result: QueryResult, context: str) -> str:
        """Generate natural language response from query results"""

        if not query_result.success:
            return f"I encountered an error: {query_result.error_message}. Could you please rephrase your question?"

        if classification["query_type"] == "definition":
            data = query_result.data
            return f"The {classification['collection']} collection {data['definition']}. It contains fields like: {', '.join(data['fields'].keys())}."

        elif classification["query_type"] == "count":
            count = query_result.data.get("count", 0)
            return f"I found {count} records in the {classification['collection']} collection."

        elif classification["query_type"] == "filter":
            count = query_result.count
            if count == 0:
                return "I didn't find any records matching your criteria."
            elif count == 1:
                return f"I found 1 record. Here's the information: {self._format_document(query_result.data[0])}"
            else:
                return f"I found {count} records. Here are some examples: {self._format_documents(query_result.data[:3])}"

        elif classification["query_type"] == "aggregation":
            if query_result.data and len(query_result.data) > 0:
                result = query_result.data[0]
                if "result" in result:
                    return f"The result is: {result['result']}"
                elif "count" in result:
                    return f"The count is: {result['count']}"
            return "I calculated the result but couldn't format it properly."

        return f"I processed your query and found {query_result.count} results."

    def _format_document(self, doc: Dict) -> str:
        """Format a single document for display"""
        formatted = []
        for key, value in doc.items():
            if key != "_id":
                if isinstance(value, list) and len(value) > 3:
                    formatted.append(f"{key}: {value[:3]} (and {len(value)-3} more)")
                else:
                    formatted.append(f"{key}: {value}")
        return " | ".join(formatted[:5])

    def _format_documents(self, docs: List[Dict]) -> str:
        """Format multiple documents for display"""
        return "\n".join([f"• {self._format_document(doc)}" for doc in docs])

    def get_insights(self) -> ConversationInsight:
        """Get insights from current conversation"""
        return self.insight_extractor.extract_insights(
            self.memory_manager.conversation_log,
            []  #here we could include query results if needed
        )

    def reset_conversation(self):
        """Reset conversation memory"""
        self.memory_manager.clear_memory()

    def disconnect(self):
        """Disconnect from database"""
        if self.client:
            self.client.close()
            logger.info(" Disconnected from MongoDB")

if __name__ == "__main__":
    # Simple test, just run on terminal, for interface run the streamlit file
    agent = ConversationalDatabaseAgent()

    if agent.connect_database():
        print("Conversational Database Agent Ready!")
        print("✅ Database connected")
        print("✅ Schema loaded")
        print("✅ NLP processor ready")

        # Test query
        response, result = agent.process_query("How many customers do we have?")
        print(f"\nTest Query: How many customers do we have?")
        print(f"Response: {response}")
        print(f"Success: {result.success}")

        agent.disconnect()
    else:
        print("❌ Failed to initialize agent")
