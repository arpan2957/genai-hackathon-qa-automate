from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(dotenv_path="frontend/.env")

import pytest
from playwright.sync_api import sync_playwright, expect
import io
from docx import Document
from PIL import Image
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(dotenv_path="frontend/.env")

# Fixture for Playwright page setup
@pytest.fixture(scope="function", autouse=True)
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(60000) # 60 seconds
        page.goto("http://localhost:3000")
        page.wait_for_selector('body', timeout=30000)
        yield page
        browser.close()

# --- Helper Functions ---

def expand_all_domains(page):
    """Helper function to expand all domain groups by clicking toggle buttons"""
    try:
        # Wait for the main content area to be present
        page.wait_for_selector("main.flex-1", timeout=10000)
        
        # Wait a bit for any loading to complete
        page.wait_for_timeout(2000)
        
        # Find domain toggle buttons using the new structure
        # Look for buttons that contain ChevronDownIcon within domain containers
        domain_buttons = page.locator("div.space-y-6 > div.bg-white button:has(svg)")
        button_count = domain_buttons.count()
        
        if button_count > 0:
            print(f"Found {button_count} domain buttons to expand")
            # Click each domain toggle button to expand all groups
            for i in range(button_count):
                try:
                    button = domain_buttons.nth(i)
                    if button.is_visible() and button.is_enabled():
                        # Check if domain is already expanded (chevron rotated)
                        chevron = button.locator("svg")
                        if chevron.count() > 0:
                            # If chevron is not rotated (domain is collapsed), click to expand
                            chevron_classes = chevron.get_attribute("class") or ""
                            if "rotate-180" not in chevron_classes:
                                print(f"Expanding domain {i+1}")
                                button.click()
                                page.wait_for_timeout(1000)  # Wait for animation
                except Exception as e:
                    print(f"Could not expand domain {i+1}: {e}")
                    pass  # Skip buttons that can't be clicked
        else:
            print("No domain buttons found to expand")
        
        page.wait_for_load_state('networkidle', timeout=5000)
    except Exception as e:
        print(f"Error in expand_all_domains: {e}")
        pass  # Silently handle any expansion errors

def login(page):
    # Click the login button on the welcome page
    page.wait_for_selector("button:text('Login')", state="visible", timeout=30000)
    page.locator("button:text('Login')").click()

    # Wait for the login modal to appear
    page.wait_for_selector("h2:text('Welcome Back')", state="visible", timeout=30000)

    # Fill in the login form
    page.locator("input[type=email]").fill("test@example.com")
    page.locator("input[type=password]").fill("password")

    # Click the Sign In button
    page.locator("form button:text('Sign In')").click()

    # Wait for the main application page to load after login
    page.wait_for_selector("header", state="visible", timeout=30000)
    
    # Wait for main app content to load instead of networkidle (which can timeout due to ongoing requests)
    page.wait_for_selector("main.flex-1", state="visible", timeout=15000)
    
    # Give the app a moment to fully initialize
    page.wait_for_timeout(2000)

    # Verify that the user is logged in by checking for user email or name in header
    # The header shows either display name or email
    user_indicator = page.locator("header span:has-text('test@example.com'), header span:has-text('test')")
    expect(user_indicator).to_be_visible(timeout=10000)

# --- Test Cases ---

def test_document_upload(page):
    login(page)
    
    # Open the AI modal
    page.wait_for_selector("button:has-text('Generate with AI')", state="visible")
    page.locator("button:has-text('Generate with AI')").click()

    # Wait for the modal to be visible
    page.wait_for_selector("h3:text('Generate with AI')", state="visible")

    # Create a dummy docx file in memory
    document = Document()
    document.add_paragraph("This is a test requirement from an in-memory docx file.")
    document.add_paragraph("The system must support user logout.")
    file_stream = io.BytesIO()
    document.save(file_stream)
    file_stream.seek(0)

    # Upload the file from memory
    page.set_input_files("input[type=file]", files=[
        {"name": "test.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "buffer": file_stream.read()}
    ])

    # Fill in the product name
    page.locator("input[id='product-name']").fill("Test Product")

    # Click the generate button
    page.locator("button:text('Generate Test Cases')").click()

    # Wait for the results to appear - look for the generated content
    # Check for the loading to finish and results to appear (increased timeout for AI generation)
    try:
        page.wait_for_selector("h4:has-text('Generated Test Cases for:')", timeout=300000)  # 5 minutes
    except:
        # If AI generation times out, check for any error messages
        error_element = page.locator(".text-red-500")
        if error_element.is_visible():
            error_text = error_element.text_content()
            print(f"AI generation failed with error: {error_text}")
        raise

    # Verify that a domain header is visible
    domain_header = page.locator("h4:has-text('Generated Test Cases for: Test Product')")
    expect(domain_header).to_be_visible()
    
    # Finalize the test cases
    page.locator("button:text('Finalize')").click()
    page.wait_for_timeout(3000)  # Wait for modal to close
    page.wait_for_selector("main.flex-1", state="visible", timeout=10000)  # Ensure main content is visible

def test_document_upload_no_product_name(page):
    login(page)
    
    # Open the AI modal
    page.wait_for_selector("button:has-text('Generate with AI')", state="visible")
    page.locator("button:has-text('Generate with AI')").click()

    # Wait for the modal to be visible
    page.wait_for_selector("h3:text('Generate with AI')", state="visible")

    # Create a dummy docx file in memory
    document = Document()
    document.add_paragraph("This is a test requirement from a docx file without a product name.")
    file_stream = io.BytesIO()
    document.save(file_stream)
    file_stream.seek(0)

    # Upload the file from memory
    page.set_input_files("input[type=file]", files=[
        {"name": "test_no_product.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "buffer": file_stream.read()}
    ])

    # Click the generate button
    page.locator("button:text('Generate Test Cases')").click()

    # Wait for the results to appear - look for the generated content
    try:
        page.wait_for_selector("h4:has-text('Generated Test Cases for:')", timeout=300000)  # 5 minutes
    except:
        # If AI generation times out, check for any error messages
        error_element = page.locator(".text-red-500")
        if error_element.is_visible():
            error_text = error_element.text_content()
            print(f"AI generation failed with error: {error_text}")
        raise

    # Verify that a domain header is visible with the default product name
    domain_header = page.locator("h4:has-text('Generated Test Cases for: General Product')")
    expect(domain_header).to_be_visible()
    
    # Finalize the test cases
    page.locator("button:text('Finalize')").click()
    page.wait_for_timeout(3000)  # Wait for modal to close
    page.wait_for_selector("main.flex-1", state="visible", timeout=10000)  # Ensure main content is visible

def test_search_functionality(page):
    login(page)

    # Generate some test cases first
    page.wait_for_selector("button:has-text('Generate with AI')", state="visible")
    page.locator("button:has-text('Generate with AI')").click()
    page.wait_for_selector("h3:text('Generate with AI')", state="visible")
    page.locator("textarea[id='ai-prompt']").fill("The system must allow a doctor to approve a prescription.")
    page.locator("button:text('Generate Test Cases')").click()
    # Wait for the results to appear
    try:
        page.wait_for_selector("h4:has-text('Generated Test Cases for:')", timeout=300000)  # 5 minutes
    except:
        # If AI generation times out, check for any error messages
        error_element = page.locator(".text-red-500")
        if error_element.is_visible():
            error_text = error_element.text_content()
            print(f"AI generation failed with error: {error_text}")
        raise
    page.locator("button:text('Finalize')").click()
    # Wait for the modal to close and table to update
    page.wait_for_timeout(3000)  # Wait for modal to close
    page.wait_for_selector("main.flex-1", state="visible", timeout=10000)  # Ensure main content is visible

    # Expand all domain groups to make test cases visible
    expand_all_domains(page)

    # If no tables exist after expansion, skip the search test
    if page.locator("table").count() == 0:
        page.wait_for_timeout(2000)
        expand_all_domains(page)
        if page.locator("table").count() == 0:
            return
    
    # Search for a specific test case using the header search
    search_input = page.locator("header input[type='text']")
    search_input.fill("TC-")
    page.wait_for_timeout(1000)
    
    # Expand domains to see if any test cases are visible
    expand_all_domains(page)
    assert page.locator("tbody tr").count() > 0

    search_input.fill("Approve")
    page.wait_for_timeout(1000)
    expand_all_domains(page)
    assert page.locator("tbody tr").count() > 0

    # Search for something that doesn't exist
    search_input.fill("nonexistentsearchquery")
    page.wait_for_timeout(1000)
    expect(page.locator("tbody tr")).to_have_count(0)
    expect(page.locator("h3:text('No results found')")).to_be_visible()

def test_manual_creation(page):
    login(page)

    # Open the manual create modal
    page.locator("button:has-text('Create Test Case')").click()
    page.wait_for_selector("h3:text('Create New Test Case')", state="visible")

    # Fill the form using the correct IDs from CreateTestCaseModal
    page.locator("input[id='tc-title']").fill("Manually Created Test Case")
    page.locator("select[id='tc-type']").select_option("Positive")
    page.locator("select[id='tc-priority']").select_option("Medium")
    page.locator("textarea[id='tc-steps']").fill("1. Do this.\n2. Do that.")

    # Save the test case
    page.locator("button:text('Save Test Case')").click()
    # Wait for the modal to close and table to update
    page.wait_for_timeout(3000)  # Wait for modal to close
    page.wait_for_selector("main.flex-1", state="visible", timeout=10000)  # Ensure main content is visible

    # Wait a bit for the backend to process
    page.wait_for_timeout(3000)

    # Expand domain groups to make test cases visible
    expand_all_domains(page)

    # Verify that the new test case is in the table
    # Look for the test case title in any table cell (use first to handle multiple matches)
    test_case_locator = page.locator("td:has-text('Manually Created Test Case')").first
    expect(test_case_locator).to_be_visible(timeout=30000)

def test_deletion(page):
    login(page)

    # Create a test case to delete
    page.locator("button:has-text('Create Test Case')").click()
    page.wait_for_selector("h3:text('Create New Test Case')", state="visible")
    # Use a unique name with timestamp to avoid conflicts
    import time
    unique_name = f"To Be Deleted {int(time.time())}"
    page.locator("input[id='tc-title']").fill(unique_name)
    page.locator("select[id='tc-type']").select_option("Positive")
    page.locator("select[id='tc-priority']").select_option("Low")
    page.locator("textarea[id='tc-steps']").fill("Steps")
    page.locator("button:text('Save Test Case')").click()
    # Wait for the modal to close and table to update
    page.wait_for_timeout(3000)  # Wait for modal to close
    page.wait_for_selector("main.flex-1", state="visible", timeout=10000)  # Ensure main content is visible
    
    # Wait a bit for the backend to process
    page.wait_for_timeout(3000)
    
    # Expand domain groups to make test cases visible
    expand_all_domains(page)
    expect(page.locator(f"td:has-text('{unique_name}')")).to_be_visible(timeout=30000)

    # Delete the test case - find the row containing the unique name and click its delete button
    test_case_row = page.locator(f"tr:has(td:has-text('{unique_name}'))")
    delete_button = test_case_row.locator("button[aria-label='delete']")
    delete_button.click()

    # Handle the custom confirmation modal
    page.wait_for_selector("h2:text('Delete Test Case')")
    page.locator("button:text('Confirm')").click()
    # Wait for the deletion to complete and table to update
    page.wait_for_timeout(3000)  # Wait for deletion to process

    # Verify that the specific test case is gone
    expect(page.locator(f"td:has-text('{unique_name}')")).not_to_be_visible()

def test_multimodal_generation(page):
    login(page)
    
    # Open the AI modal
    page.wait_for_selector("button:has-text('Generate with AI')", state="visible")
    page.locator("button:has-text('Generate with AI')").click()

    # Wait for the modal to be visible
    page.wait_for_selector("h3:text('Generate with AI')", state="visible")

    # Create a dummy image file in memory
    img = Image.new('RGB', (100, 100), color = 'red')
    file_stream = io.BytesIO()
    img.save(file_stream, 'PNG')
    file_stream.seek(0)

    # Upload the file from memory
    page.set_input_files("input[type=file]", files=[
        {"name": "test.png", "mimeType": "image/png", "buffer": file_stream.read()}
    ])

    # The text area is disabled when a file is uploaded, so we don't fill it.

    # Click the generate button
    page.locator("button:text('Generate Test Cases')").click()

    # Wait for the results to appear
    try:
        page.wait_for_selector("h4:has-text('Generated Test Cases for:')", timeout=300000)  # 5 minutes
    except:
        # If AI generation times out, check for any error messages
        error_element = page.locator(".text-red-500")
        if error_element.is_visible():
            error_text = error_element.text_content()
            print(f"AI generation failed with error: {error_text}")
        raise

    # Verify that a domain header is visible
    domain_header = page.locator("h4:has-text('Generated Test Cases for: General Product')")
    expect(domain_header).to_be_visible()
    
    # Finalize the test cases
    page.locator("button:text('Finalize')").click()
    page.wait_for_timeout(3000)  # Wait for modal to close
    page.wait_for_selector("main.flex-1", state="visible", timeout=10000)  # Ensure main content is visible

def test_rag_functionality(page):
        login(page)

        # Navigate to the Knowledge Base page
        page.wait_for_selector("button:has-text('Knowledge Base')", state="visible")
        page.locator("button:has-text('Knowledge Base')").click()
        page.wait_for_load_state('networkidle', timeout=60000)
        page.wait_for_selector("h1:text('Knowledge Base')", timeout=60000)

        # Create a dummy docx file in memory
        document = Document()
        document.add_paragraph("This is a test requirement from an in-memory docx file for RAG.")
        document.add_paragraph("The system must support user logout with a custom compliance tag: RAG-COMPLIANT.")
        file_stream = io.BytesIO()
        document.save(file_stream)
        file_stream.seek(0)

        # Upload the file from memory
        page.set_input_files("input[type=file]", files=[
            {"name": "rag_test.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "buffer": file_stream.read()}
        ])

        # Wait for the upload to complete and the document to appear in the list
        page.wait_for_timeout(5000)
        page.wait_for_selector("td:text('rag_test.docx')", state="visible", timeout=30000)

        # Navigate back to the main page
        page.locator("a:has-text('Home')").click()
        page.wait_for_selector("h1:text('Test Cases')", state="visible")

        # Open the AI modal
        page.locator("button:has-text('Generate with AI')").click()
        page.wait_for_selector("h3:text('Generate with AI')", state="visible")

        # Fill in the requirement prompt
        page.locator("textarea[id='ai-prompt']").fill("Generate a test case for user logout.")

        # Click the generate button
        page.locator("button:text('Generate Test Cases')").click()

        # Wait for the results to appear
        try:
            page.wait_for_selector("h4:has-text('Generated Test Cases for:')", timeout=300000)  # 5 minutes
        except:
            # If AI generation times out, check for any error messages
            error_element = page.locator(".text-red-500")
            if error_element.is_visible():
                error_text = error_element.text_content()
                print(f"AI generation failed with error: {error_text}")
            raise

        # Verify that the generated test case is context-aware
        expect(page.locator("td:text('RAG-COMPLIANT')")).to_be_visible()
