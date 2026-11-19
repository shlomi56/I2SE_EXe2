# Ex2: Vibe Coding & Deep Designing: Web-based Teaching Tool

## 1. Problem Definition
The current landscape of online teaching tools is cumbersome and failing to meet the dynamic needs of modern classrooms. Existing platforms are often bloated, overly complex, and lack seamless integration with modern Artificial Intelligence (LLM) capabilities. 

Valuable class time is wasted on manual administrative tasks like attendance tracking. Furthermore, students lack a frictionless way to interact in real-time or receive deep, personalized feedback on their assignments. The overarching problem is the absence of a simple, centralized, and "LLM-ready" tool that allows lecturers to focus on teaching and students to focus on learning without technological friction.

## 2. Project Scope
The scope of this project is to design and demonstrate an end-to-end, Keep It Simple, Stupid (KISS) web-based application optimized for smartphone use in a classroom setting. The system will operate as a standalone platform focused purely on the core learning and administrative experience.

**In-Scope (Core Features):**
1. **Automated Attendance:** A simple camera interface allowing the lecturer to capture a photo of the class. The system uses local computer vision (MediaPipe) for automatic student counting, generating an instant offline/online spreadsheet of attendance details.
2. **Live/Offline Interaction:** A persistent, real-time feed (via Firebase) where students can post comments and raise suggestions during or after the lecture.
3. **On-the-Spot Polling:** A quick-deployment polling system for lecturers to gauge student understanding instantly, using lightweight cloud state management.
4. **ML Lecture Summarization:** A feature to process uploaded recorded class videos/audio and generate automated Machine Learning summaries using a multimodal LLM (Gemini 1.5 Flash).
5. **Deep LLM Homework Review:** An automated code-review system where students paste or upload their raw code directly into the web application. The system securely pools these submissions in a lightweight cloud database to dynamically build a repository of anonymous peer code for the LLM to use in comparative analysis.

**Out of Scope:**
* **Third-Party Platform Integrations:** The application will not integrate with external university management systems such as Moodle, personal information systems (מידע אישי), or live plugins for Zoom/Meet.
* **Native Mobile Applications:** The solution will be strictly a web-based application (accessible via mobile browsers), avoiding native iOS or Android development.
* **Complex Implementation/Coding:** The focus is strictly on the design, architecture, and composing ("vibe coding") a functional demo.
* **Version Control Integration:** The application will not use the GitHub API or require students to submit repository URLs, strictly adhering to the KISS principle by keeping code ingestion entirely within the application.
* **User Authentication:** No complex login systems; simple role-based routing (Student vs. Lecturer) will be used.

## 3. Tech Stack
* **Frontend/Framework:** Streamlit (Python) for a responsive, mobile-friendly web interface.
* **Backend Database:** Firebase Realtime Database (for comments, polls, and anonymous code pooling).
* **Machine Learning / AI:** 
  * Google MediaPipe (Local Face Detection for counting).
  * Google Gemini API (Multimodal Video Summarization and Code Review).