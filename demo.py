"""
Demo Script for Conversational Database Agent
Runs predefined queries to demonstrate the agent's capabilities
"""

import time
import json
from typing import List, Dict
from database_agent import ConversationalDatabaseAgent
from config import config

class AgentDemo:
    """Demonstrates the agent with predefined scenarios"""

    def __init__(self, use_mock_data: bool = False):
        self.agent = ConversationalDatabaseAgent()
        self.use_mock_data = use_mock_data
        self.demo_queries = [
            "What is the accounts collection?",
            "How many customers do we have?",
            "Show me information about customer accounts",
            "What's the average account limit?",
            "How many accounts have InvestmentStock products?",
            "Find customers with high account limits",
            "What products are available in the accounts?",
            "Show me recent customer information"
        ]

    def setup_mock_data(self):
        """Setup mock data for testing when MongoDB is not available"""

        mock_schema = {
            "accounts": {
                "document_count": 1746,
                "fields": {
                    "_id": {"type": "ObjectId"},
                    "account_id": {"type": "int"},
                    "limit": {"type": "int"},
                    "products": {"type": "list"}
                }
            },
            "customers": {
                "document_count": 500,
                "fields": {
                    "_id": {"type": "ObjectId"},
                    "username": {"type": "str"},
                    "name": {"type": "str"},
                    "email": {"type": "str"},
                    "accounts": {"type": "list"}
                }
            },
            "transactions": {
                "document_count": 1746,
                "fields": {
                    "_id": {"type": "ObjectId"},
                    "account_id": {"type": "int"},
                    "transaction_count": {"type": "int"},
                    "bucket_start_date": {"type": "datetime"},
                    "transactions": {"type": "list"}
                }
            }
        }

        
        if self.agent.schema_manager:
            self.agent.schema_manager.schema_cache = mock_schema

    def run_demo(self):
        """Run the complete demo"""

        self.display_header()

        
        if self.use_mock_data:
            print(" Using mock data for demonstration")
            self.agent.schema_manager = type('MockSchema', (), {})()
            self.setup_mock_data()
            connected = True
        else:
            print("✅ Connecting to MongoDB...")
            connected = self.agent.connect_database()

        if not connected and not self.use_mock_data:
            print("❌ Could not connect to database. Running with mock data...(check demo.py file to see the mock data)")
            self.use_mock_data = True
            self.setup_mock_data()

        print("✅ Ready to demonstrate!")
        print("-" * 60)

    
        for i, query in enumerate(self.demo_queries, 1):
            self.run_demo_query(i, query)
            time.sleep(1)  # Brief pause between queries

        
        self.show_demo_insights()

        
        if not self.use_mock_data:
            self.agent.disconnect()

        self.display_footer()

    def display_header(self):
        """Display demo header"""
        print(" " + "=" * 58 + " ")
        print("           CONVERSATIONAL DATABASE AGENT DEMO")
        print(" " + "=" * 58 + " ")
        print()
        print("This demo will show the agent's capabilities:")
        print("• Natural language query processing")
        print("• Schema understanding")
        print("• Query classification and execution")
        print("• Conversation memory")
        print("• Insight extraction")
        print()

    def run_demo_query(self, query_num: int, query: str):
        """Run a single demo query"""

        print(f"\n Query {query_num}: {query}")
        print("-" * 40)

        try:
            if self.use_mock_data:
                
                response = self.generate_mock_response(query)
                print(f" Response: {response}")
               
                time.sleep(0.5)

                print(f"✅ Query processed successfully")

            else:
                
                start_time = time.time()
                #start_time=time.time()
                response, result = self.agent.process_query(query)

                execution_time = time.time() - start_time

                print(f" Response: {response}")

                if result.success:
                    print(f"✅ Query executed successfully")
                    print(f" Results: {result.count} items")
                    print(f"  Execution time: {execution_time:.2f}s")
                else:
                    print(f"❌ Query failed: {result.error_message}")

        except Exception as e:
            print(f"❌ Error processing query: {e}")

    def generate_mock_response(self, query: str) -> str:#I did use AI to generate the mock responses here!
        """Generate mock responses for demo purposes"""

        query_lower = query.lower()

        if "what is" in query_lower and "collection" in query_lower:
            return "The accounts collection contains customer account information including credit limits and financial products like InvestmentStock, CurrencyService, and Derivatives."

        elif "how many customers" in query_lower:
            return "I found 500 customers in the database."

        elif "average" in query_lower and "limit" in query_lower:
            return "The average account limit is $9,124.32 across all accounts."

        elif "investmentstock" in query_lower:
            return "I found 348 accounts that have InvestmentStock products."

        elif "high" in query_lower and "limit" in query_lower:
            return "I found 23 customers with account limits above $15,000. Here are some examples: John Smith (limit: $18,500), Sarah Johnson (limit: $22,100)."

        elif "products" in query_lower:
            return "The available products include: InvestmentStock, CurrencyService, Derivatives, Commodity, and Brokerage services."

        elif "recent" in query_lower:
            return "Here are some recent customers: Alice Williams (joined last month), Bob Chen (account opened 2 weeks ago), Carol Davis (updated profile yesterday)."

        else:
            return "I processed your query and found relevant information in the database."

    def show_demo_insights(self):
        """Show conversation insights"""

        print("\n" + "=" * 60)
        print(" CONVERSATION INSIGHTS")
        print("=" * 60)

        if self.use_mock_data:
            # Mock insights
            print(" User Intent: Exploring database structure and querying financial data")
            print("Emotional Tone: Curious and engaged")
            print(" Data Gaps Identified:")
            print("   • User might want to see specific customer details")
            print("   • Transaction analysis could be valuable")
            print("   • Product performance metrics are missing")
            print(" Suggested Follow-up Questions:")
            print("   • What are the most popular products?")
            print("   • Show me transaction patterns over time")
            print("   • Find customers with the highest transaction volumes")
        else:
            try:
                insights = self.agent.get_insights()
                print(f" User Intent: {insights.user_intent}")
                print(f" Emotional Tone: {insights.emotional_tone}")

                if insights.data_gaps:
                    print("🔍 Data Gaps:")
                    for gap in insights.data_gaps:
                        print(f"   • {gap}")

                if insights.suggested_queries:
                    print(" Suggested Questions:")
                    for suggestion in insights.suggested_queries:
                        print(f"   • {suggestion}")
            except Exception as e:
                print(f"Could not extract insights: {e}")

    def display_footer(self):
        """Display demo footer"""

        print("\n" + "=" * 60)
        print(" DEMO COMPLETED!")
        print("=" * 60)
        print("The Conversational Database Agent demonstrated:")
        print("✅ Natural language understanding")
        print("✅ MongoDB query translation")
        print("✅ Conversation memory")
        print("✅ Insight extraction")
        print("✅ Error handling")
        print()
        print("Ready for production use! 🚀")
        print("=" * 60)

def run_interactive_demo():
    """Run an interactive demo where user can choose queries"""

    demo = AgentDemo()

    print(" INTERACTIVE DEMO MODE")
    print("Choose queries to run, or run all automatically")
    print()

    for i, query in enumerate(demo.demo_queries, 1):
        print(f"{i}. {query}")

    print("\nOptions:")
    print("• Enter query numbers (e.g., 1,3,5)")
    print("• Type 'all' to run all queries")
    print("• Type 'mock' to use mock data")

    choice = input("\nYour choice: ").strip().lower()

    if choice == 'mock':
        demo.use_mock_data = True
        demo.run_demo()
    elif choice == 'all':
        demo.run_demo()
    else:
        try:
            
            query_nums = [int(x.strip()) for x in choice.split(',')]
            selected_queries = [demo.demo_queries[i-1] for i in query_nums if 1 <= i <= len(demo.demo_queries)]

            if selected_queries:
                demo.demo_queries = selected_queries
                demo.run_demo()
            else:
                print("No valid queries selected.")
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")

def main():
    """Main entry point"""

    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--mock':
            # Run with mock data
            demo = AgentDemo(use_mock_data=True)
            demo.run_demo()
        elif sys.argv[1] == '--interactive':
            # Run interactive mode
            run_interactive_demo()
        else:
            print("Usage: python demo.py [--mock|--interactive]")
    else:
    
        demo = AgentDemo()
        demo.run_demo()

if __name__ == "__main__":
    main()
