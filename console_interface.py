"""
Console Interface for Conversational Database Agent
Provides an interactive command-line interface for testing the agent
"""

import sys
import time
from typing import Dict, Any
from database_agent import ConversationalDatabaseAgent
from config import config

class ConsoleInterface:
    """Interactive console interface for the database agent"""

    def __init__(self):
        self.agent = ConversationalDatabaseAgent()
        self.running = False

    def display_banner(self):
        """Display welcome banner"""
        print("=" * 60)
        print(" CONVERSATIONAL DATABASE AGENT")
        print("=" * 60)
        print("Chat with your MongoDB database using natural language!")
        print("Database:", config.database.database_name)
        print("Model:", config.llm.model)
        print("=" * 60)

    def display_help(self):
        """Display help information"""
        print("\n HELP - Available Commands:")
        print("🔸 Ask any question about your data")
        print("🔸 'help' - Show this help message")
        print("🔸 'insights' - Show conversation insights")
        print("🔸 'reset' - Clear conversation history")
        print("🔸 'schema' - Show database schema")
        print("🔸 'examples' - Show example queries")
        print("🔸 'quit' or 'exit' - Exit the application")
        print("-" * 60)

    def display_examples(self):
        """Display example queries"""
        examples = [
            "What is the accounts collection?",
            "How many customers do we have?",
            "Show me all customers",
            "What's the average account limit?",
            "Find customers with email addresses",
            "How many accounts have InvestmentStock products?",
            "Show me recent transactions",
            "What products are available?"
        ]

        print("\n EXAMPLE QUERIES:")
        for i, example in enumerate(examples, 1):
            print(f"{i:2d}. {example}")
        print("-" * 60)

    def display_schema_info(self):
        """Display database schema information"""
        print("\n DATABASE SCHEMA:")

        if not self.agent.schema_manager:
            print("❌ Schema manager not initialized")
            return

        schema = self.agent.schema_manager.schema_cache
        if not schema:
            print(" Discovering schema...")
            schema = self.agent.schema_manager.discover_schema()

        for collection_name, info in schema.items():
            print(f"\n Collection: {collection_name}")
            print(f"   Documents: {info.get('document_count', 'Unknown')}")

            fields = info.get('fields', {})
            print(f"   Fields ({len(fields)}):")
            for field_name, field_info in list(fields.items())[:5]:
                print(f"     • {field_name}: {field_info.get('type', 'unknown')}")

            if len(fields) > 5:
                print(f"     ... and {len(fields) - 5} more fields")

        print("-" * 60)

    def display_insights(self):
        """Display conversation insights"""
        print("\n CONVERSATION INSIGHTS:")

        if not self.agent.memory_manager.conversation_log:
            print("No conversation history available yet.")
            return

        insights = self.agent.get_insights()

        print(f" User Intent: {insights.user_intent}")
        print(f" Emotional Tone: {insights.emotional_tone}")

        if insights.data_gaps:
            print(" Data Gaps:")
            for gap in insights.data_gaps:
                print(f"   • {gap}")

        if insights.suggested_queries:
            print(" Suggested Questions:")
            for suggestion in insights.suggested_queries:
                print(f"   • {suggestion}")

        print("-" * 60)

    def process_command(self, user_input: str) -> bool:
        """Process user command and return whether to continue"""

        user_input = user_input.strip().lower()

        if user_input in ['quit', 'exit', 'bye']:
            return False

        elif user_input == 'help':
            self.display_help()

        elif user_input == 'reset':
            self.agent.reset_conversation()
            print("✅ Conversation history cleared")

        elif user_input == 'schema':
            self.display_schema_info()

        elif user_input == 'examples':
            self.display_examples()

        elif user_input == 'insights':
            self.display_insights()

        elif user_input == '':
            # if empty input, just continue
            pass

        else:
            # Process as a query, duh
            self.process_query(user_input)

        return True

    def process_query(self, query: str):
        """Process a natural language query"""
        print(" Thinking...")

        start_time = time.time()

        try:
            response, result = self.agent.process_query(query)

            execution_time = time.time() - start_time

            print(f"\n Assistant: {response}")

            if config.agent.debug_mode and result:
                print(f"\n Debug Info:")
                print(f"   Query Type: {result.query_type}")
                print(f"   Success: {result.success}")
                print(f"   Count: {result.count}")
                print(f"   Execution Time: {result.execution_time_ms:.2f}ms")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try rephrasing your question.")

        print("-" * 60)

    def run(self):
        """Run the interactive console interface"""

        self.display_banner()

        # Initialize agent
        print(" Connecting to database...")
        if not self.agent.connect_database():
            print("❌ Failed to connect to database. Please check your configuration.")
            return

        print("✅ Connected successfully!")
        print(" You can start asking questions. Type 'help' for assistance.")

        self.running = True

        try:
            while self.running:
                print()  ##spacing
                user_input = input("👤 You: ").strip()

                if not self.process_command(user_input):
                    break

        except KeyboardInterrupt:
            print("\n\n Interrupted by user")

        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")

        finally:
            print("\nDisconnecting...")
            self.agent.disconnect()

def main():
    """Main entry point"""

    # Check if configuration is valid
    from config import validate_config

    if not validate_config():
        print("❌ Configuration validation failed. Please check your .env file.(Need to have all the credentials and the hyperparameters correctly filled in the .env file)")
        sys.exit(1)

    interface = ConsoleInterface()
    interface.run()

if __name__ == "__main__":
    main()
