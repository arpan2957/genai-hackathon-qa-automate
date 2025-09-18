
import os
import firebase_admin
from firebase_admin import credentials, auth, firestore
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Firebase Admin SDK Initialization ---
# Make sure to set the GOOGLE_APPLICATION_CREDENTIALS environment variable
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()

def cleanup_user_test_cases(email: str):
    """
    Deletes all finalized test case documents for a given user email.
    """
    try:
        # Get the user by email
        user = auth.get_user_by_email(email)
        print(f"Found user: {user.uid} ({user.email})")

        # Get a reference to the user's finalized_cases collection
        docs_ref = db.collection('users').document(user.uid).collection('finalized_cases')
        
        # Get all documents in the collection
        docs = list(docs_ref.stream())

        if not docs:
            print("No finalized test cases found for this user.")
            return

        print(f"Found {len(docs)} documents to delete...")

        # Delete each document
        for doc in docs:
            print(f"Deleting document: {doc.id}")
            doc.reference.delete()

        print("Cleanup complete!")

    except auth.UserNotFoundError:
        print(f"Error: User with email {email} not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    user_email = "test@example.com"
    print(f"Starting cleanup for user: {user_email}")
    cleanup_user_test_cases(user_email)
