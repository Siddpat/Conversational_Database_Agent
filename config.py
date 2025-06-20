"""
Configuration module for the Conversational Database Agent
Manages environment variables, database settings, and LLM parameters
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

##
# Load environment variables from .env file
load_dotenv()

@dataclass
class DatabaseConfig:
    """MongoDB database configuration"""
    connection_string: str 
    database_name: str
    timeout_ms: int = 5000
    max_pool_size: int = 50

@dataclass  
class LLMConfig:
    """LLM (OpenAI) configuration"""
    api_key: str
    model: str 
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 30

@dataclass
class AgentConfig:
    """Agent behavior configuration"""
    max_conversation_history: int = 20
    max_query_results: int = 50
    enable_streaming: bool = True
    debug_mode: bool = False

class Config:
    """Main configuration class"""

    def __init__(self):
        self.database = self._get_database_config()
        self.llm = self._get_llm_config() 
        self.agent = self._get_agent_config()

    def _get_database_config(self) -> DatabaseConfig:
        """Get database configuration from environment variables"""
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        if not connection_string:
            # Default connection string for local development. Dunno, given on the web
            connection_string = "mongodb://localhost:27017/"
            print("  Using default MongoDB connection. Set MONGODB_CONNECTION_STRING for Atlas.")

        return DatabaseConfig(
            connection_string=connection_string,
            database_name=os.getenv("MONGODB_DATABASE", "sample_analytics"),
            timeout_ms=int(os.getenv("MONGODB_TIMEOUT_MS", "5000")),
            max_pool_size=int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
        )

    def _get_llm_config(self) -> LLMConfig:
        """Get LLM configuration from environment variables"""
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        return LLMConfig(
            api_key=api_key,
            #config_list=[{
            #"api_type": "openai",
            #"model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            #"api_key": api_key,
            #}],
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),            
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS","2000")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30"))
        )

    def _get_agent_config(self) -> AgentConfig:
        """Get agent configuration from environment variables"""
        return AgentConfig(
            max_conversation_history=int(os.getenv("MAX_CONVERSATION_HISTORY", "20")),
            max_query_results=int(os.getenv("MAX_QUERY_RESULTS", "50")),
            enable_streaming=os.getenv("ENABLE_STREAMING", "true").lower() == "true",
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true"
        )

# Global configuration instance
config = Config()

# Sample analytics database schema metadata
SAMPLE_ANALYTICS_SCHEMA = {
    "accounts": {
        "description": "Customer account information including credit limits and products",
        "fields": {
            "_id": {"type": "ObjectId", "description": "Unique account identifier"},
            "account_id": {"type": "int", "description": "Account ID number"},
            "limit": {"type": "int", "description": "Credit limit for the account"},
            "products": {"type": "array", "description": "Array of financial products (CurrencyService, Derivatives, InvestmentStock, etc.)"}
        },
        "relationships": {
            "customers": "Referenced by customers.accounts array"
        }
    },
    "customers": {
        "description": "Customer profile information and contact details",
        "fields": {
            "_id": {"type": "ObjectId", "description": "Unique customer identifier"},
            "username": {"type": "string", "description": "Customer username"},
            "name": {"type": "string", "description": "Customer full name"},
            "address": {"type": "string", "description": "Customer address"},
            "birthdate": {"type": "date", "description": "Customer birth date"},
            "email": {"type": "string", "description": "Customer email address"},
            "accounts": {"type": "array", "description": "Array of account IDs belonging to this customer"},
            "tier_and_details": {"type": "object", "description": "Customer tier information and additional details"}
        },
        "relationships": {
            "accounts": "customers.accounts[] -> accounts.account_id"
        }
    },
    "transactions": {
        "description": "Financial transaction records with amounts and dates",
        "fields": {
            "_id": {"type": "ObjectId", "description": "Unique transaction identifier"},
            "account_id": {"type": "int", "description": "Account ID for the transaction"},
            "transaction_count": {"type": "int", "description": "Number of transactions"},
            "bucket_start_date": {"type": "date", "description": "Start date for transaction bucket"},
            "bucket_end_date": {"type": "date", "description": "End date for transaction bucket"},
            "transactions": {"type": "array", "description": "Array of individual transactions with amounts and dates"}
        },
        "relationships": {
            "accounts": "transactions.account_id -> accounts.account_id"
        }
    }
}

# Query type classifications
QUERY_TYPES = {
    "definition": "Explain what a field, collection, or concept means",
    "filter": "Find documents matching specific criteria",
    "aggregation": "Calculate statistics like sum, average, count, min, max",
    "count": "Count documents or records",
    "trend": "Analyze patterns over time",
    "comparison": "Compare different groups or values"
}

# Sample queries for few-shot prmpting
SAMPLE_QUERIES = {
    "What is the accounts collection?": {
        "type": "definition",
        "query": None,
        "response": "The accounts collection contains customer account information including credit limits and financial products."
    },
    "Show me all customers": {
        "type": "filter", 
        "query": {"collection": "customers", "operation": "find", "filter": {}},
        "response": "Here are all customers in the database"
    },
    "How many customers do we have?": {
        "type": "count",
        "query": {"collection": "customers", "operation": "count_documents", "filter": {}},
        "response": "Total number of customers"
    },
    "What's the average account limit?": {
        "type": "aggregation",
        "query": {"collection": "accounts", "operation": "aggregate", "pipeline": [{"$group": {"_id": None, "avg_limit": {"$avg": "$limit"}}}]},
        "response": "Average account limit across all accounts"
    }
}

def validate_config() -> bool:
    """Validate that all required configuration is present"""
    try:
        config = Config()
        return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False

if __name__ == "__main__":
    print(" Configuration Test")
    print("=" * 50)

    if validate_config():
        print("✅ Configuration is valid")
        print(f"Database: {config.database.database_name}")
        print(f"LLM Model: {config.llm.model}")
        print(f"Debug Mode: {config.agent.debug_mode}")
    else:
        print("❌ Configuration validation failed")
