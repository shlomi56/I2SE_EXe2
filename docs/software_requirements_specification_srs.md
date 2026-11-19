# Software Requirements Specification (SRS)

## 1. Functional Requirements
* **REQ-1 (Attendance):** The system shall allow the lecturer to capture an image and automatically return an integer count of detected faces, downloadable as a `.csv` spreadsheet.
* **REQ-2 (Comments):** The system shall provide a shared, real-time text feed that updates without requiring a page refresh and persists data for offline viewing.
* **REQ-3 (Polls):** The system shall allow the lecturer to push a multi-choice question to all connected student clients and display the aggregated results.
* **REQ-4 (Summary):** The system shall accept media file uploads and return a markdown-formatted summary utilizing an LLM API.
* **REQ-5.1 (Review Input):** The system shall provide a text interface for users to input raw source code.
* **REQ-5.2 (Review Storage):** The system shall automatically push the submitted text to a shared database node (Cloud Pool) upon submission.
* **REQ-5.3 (Review Context):** The system shall fetch at least one prior anonymous submission from the database to serve as peer context.
* **REQ-5.4 (Review Output):** The system shall prompt the LLM with both the current submission and the peer context to generate a comparative analysis report.

## 2. Non-Functional Requirements
* **Usability:** The UI must be responsive and fully operable on a standard smartphone web browser (KISS principle).
* **Performance:** MediaPipe face detection must run locally and return a count within 5 seconds. LLM media summarization must return within 2 minutes for short clips.
* **Security:** No API keys or service account credentials shall be exposed in the client-side code or version control.

## 3. Main Software Components
* **`StreamlitUI` (Frontend):** The main entry point rendering the mobile-friendly web interface and handling route toggles (Lecturer vs. Student views).
* **`MediaPipeController` (Backend):** Handles image array processing, configures the confidence threshold, and executes the face counting logic.
* **`CloudPoolManager` (Backend):** A dedicated module responsible for all read/write operations to the Firebase Realtime Database (handling comments, polls, and anonymous code pooling).
* **`GeminiService` (Backend):** Handles prompt orchestration and API calls to Google's generative models for both the video summarization and the comparative code review.

## 4. Main Use Cases (Client Stories)

**Use Case 1: Automated Class Count**
* **Actor:** Lecturer
* **Trigger:** Lecturer wants to take attendance at the start of class.
* **Scenario:** Lecturer selects the "Lecturer" role, opens the "Attendance" tab, and points their smartphone camera at the class. They tap "Capture". The system processes the image via MediaPipe, overlays bounding boxes for visual verification, and displays the total count. The lecturer taps "Download CSV" to save the record.

**Use Case 2: Comparative Homework Review**
* **Actor:** Student
* **Trigger:** Student finishes their assignment in their local IDE and wants feedback before final submission.
* **Scenario:** Student copies their code and pastes it into the web app's text area. The `CloudPoolManager` saves this code anonymously to the database. The system then retrieves a previously saved code snippet from the pool. The `GeminiService` packages both snippets and prompts the LLM. Finally, the app displays a structured Markdown review comparing the student's approach to their peer's approach.