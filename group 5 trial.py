import os
import requests
import webbrowser  # Import the webbrowser module
from django.shortcuts import render
from django.http import JsonResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Authenticate entrepreneur data with Google Forms API
def authenticate_google_forms():
    SCOPES = ['https://www.googleapis.com/auth/forms.body',
              'https://www.googleapis.com/auth/forms.responses.readonly']
    creds = None

    # Check if credentials.json exists
    if os.path.exists('credentials.json'):
        creds = Credentials.from_authorized_user_file('credentials.json', SCOPES)

    # If credentials are invalid or missing, prompt the user to log in
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            r'c:\Users\erick\OneDrive\Desktop\Group5\client_secret_197842807017-r4ma6d4484nfove2arqfsoujj7v0d4rf.apps.googleusercontent.com.json',
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open('credentials.json', 'w') as token:
            token.write(creds.to_json())

    # Build the Google Forms API service
    service = build('forms', 'v1', credentials=creds)
    return service

# Fetch form structure
def fetch_form_structure():
    structure = [
        {"type": "text", "question": "Full Name", "required": True},
        {"type": "text", "question": "Email", "required": True},
        {"type": "text", "question": "Organization", "required": True},
        {"type": "text", "question": "Project Title and description in 350 words or less", "required": True},
        {"type": "text", "question": "Why should your project be selected", "required": True}
    ]
    return structure

# Create Google Form
def create_google_form(service, form_structure):
    try:
        # Create a blank form
        form = {"info": {"title": "Grant Application Form"}}
        result = service.forms().create(body=form).execute()
        form_id = result['formId']
        form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        print(f"✅ Form created: {form_url}")

        # Add questions based on structure
        requests = []
        for idx, field in enumerate(form_structure):
            request = {
                "createItem": {
                    "item": {
                        "title": field["question"],
                        "questionItem": {
                            "question": {
                                "required": field["required"],
                                "textQuestion": {"paragraph": False}
                                if len(field["question"]) < 350 else {"paragraph": True},
                            }
                        }
                    },
                    "location": {"index": idx}
                }
            }
            requests.append(request)

        if requests:
            service.forms().batchUpdate(
                formId=form_id,
                body={'requests': requests}
            ).execute()

        print("✅ Questions added to the form.")

        # Automatically open the form in the browser
        webbrowser.open(form_url)

        return form_id
    except Exception as e:
        print(f"❌ An error occurred while creating the form: {e}")
        return None

# Process form responses and validate
def process_responses(service, form_id, form_structure):
    try:
        # Fetch responses from the form
        responses = service.forms().responses().list(formId=form_id).execute().get('responses', [])
        if not responses:
            print("No responses found.")
            return

        # Get question IDs mapped to their titles
        form = service.forms().get(formId=form_id).execute()
        question_id_map = {}
        for item in form.get("items", []):
            title = item.get("title")
            question_id = item.get("questionItem", {}).get("question", {}).get("questionId")
            if title and question_id:
                question_id_map[title] = question_id

        # Validate and process each response
        for response in responses:
            answers = response.get("answers", {})
            validated_data = {}
            valid = True

            for field in form_structure:
                Q = question_id_map.get(field["question"])
                answer_obj = answers.get(Q, {})
                answer = answer_obj.get("textAnswers", {}).get("answers", [{}])[0].get("value", "")

                # Validation check
                if field["required"] and not answer.strip():
                    print(f"❌ Validation failed: Missing {field['question']}")
                    valid = False
                    break
                validated_data[field["question"]] = answer

            if valid:
                # Submit to grant website
                submit_url = "https://boilerplate-grant-website.com/submit"
                try:
                    res = requests.post(submit_url, json=validated_data, timeout=5)
                    if res.status_code == 200:
                        print("✅ Data submitted successfully!")
                    else:
                        print(f"❌ Submission failed. Status code: {res.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"❌ Request exception occurred: {e}")
    except Exception as e:
        print(f"❌ An error occurred while processing responses: {e}")

# Django view to create form
def create_form_view(request):
    try:
        service = authenticate_google_forms()
        form_structure = fetch_form_structure()
        form_id = create_google_form(service, form_structure)
        if form_id:
            return JsonResponse({"message": "Form created successfully!", "form_url": f"https://docs.google.com/forms/d/{form_id}/edit"})
        else:
            return JsonResponse({"error": "Failed to create form."})
    except Exception as e:
        return JsonResponse({"error": str(e)})

# Main execution
if __name__ == "__main__":
    try:
        service = authenticate_google_forms()
        if service:
            form_structure = fetch_form_structure()
            form_id = create_google_form(service, form_structure)
            if form_id:
                process_responses(service, form_id, form_structure)
    except Exception as e:
        print(f"❌ An error occurred: {e}") 