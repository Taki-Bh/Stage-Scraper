from playwright.sync_api import sync_playwright
from app.core.config import *
from app.services.job_service import *
from app.workflows.orchestrator import *
if __name__ == "__main__" :
    orchestrator = PipelineOrchestrator()
    
    orchestrator.run_pipeline("Software Engineer")
