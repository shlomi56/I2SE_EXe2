# Statement of Work (SoW)
**Project:** Web-based Teaching Tool (Ex2)

## 1. Project Objectives
Design and compose a lightweight, LLM-ready web application to replace cumbersome teaching tools. The project emphasizes the "vibe coding" methodology, prioritizing system architecture, design, and a live KISS (Keep It Simple, Stupid) demonstration over manual, heavy coding.

## 2. Deliverables by Feature

**Feature 1: Automated Attendance**
* A web-based camera UI for the lecturer.
* Local integration with MediaPipe Face Detection to count visible faces.
* Automated generation and download of a `.csv` file containing the attendance timestamp and total count.

**Feature 2: Real-Time Comments**
* A text input interface for students to submit questions.
* Integration with a NoSQL cloud database (Firebase) to store and stream comments.
* An "Offline Q&A" view allowing access to historical comments after the lecture.

**Feature 3: On-the-Spot Polls**
* A rapid poll-creation form for the lecturer.
* Real-time state broadcasting to student devices to collect and aggregate votes instantly.

**Feature 4: ML Video Summary**
* A media upload component accepting `.mp4`, `.mp3`, or `.wav` files.
* Direct integration with the Gemini Multimodal API to bypass separate transcription services and generate a structured summary (Concepts, Q&A, Action Items).

**Feature 5: Deep LLM Homework Review (Cloud Pool Approach)**
* A Frontend UI text area / file upload component for direct code submission.
* Integration with Firebase Realtime Database to store and retrieve anonymous text payloads (the Cloud Pool).
* A backend service that dynamically fetches peer context from the pool and prompts the LLM to output a comparative review.

## 3. Security and Architecture Constraints
* A backend service that utilizes environment variables via a `.env` file to securely manage database credentials (Firebase JSON) and LLM API keys. 
* Credentials will never be hardcoded into the repository. A `.env.example` file will be provided for documentation purposes.

## 4. Exclusions (Out of Scope)
* Direct integrations with university databases.
* User Authentication for Code Submission: Code is dropped anonymously into the cloud pool; tracking individual student identities for the peer comparison database is out of scope.
* Use of the GitHub REST API or URL parsing for assignment fetching.