import sys
import os

# Add the project root to python path so we can import tests.ingest_receiver
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.ingest_receiver import IngestReceiver
from scraper.scraper_agent import ScraperAgent
from client.onion_client import OnionClient

def run_3_times():
    print("Starting IngestReceiver...")
    with IngestReceiver() as receiver:
        ingest_url = receiver.url
        print(f"Receiver started at {ingest_url}")
        for i in range(3):
            print(f"\\n--- RUN {i+1} ---")
            client = OnionClient("http://localhost:8000")
            agent = ScraperAgent(client=client, ingest_url=ingest_url)
            summary = agent.run()
            print(summary.render())

if __name__ == "__main__":
    run_3_times()
