# DBPShit API Documentation

This documentation outlines the API endpoints used by the `dbpshit-client` application.

**Base URL**: `https://dbapi.ptit.edu.vn/api` (Inferred)

## Authentication

All requests (except login) require a Bearer Token in the `Authorization` header.
- **Header**: `Authorization: Bearer <token>`
- **Token Source**: Obtained via Selenium login from `localStorage` or `sessionStorage`.

---

## Endpoints

### 1. Get Question Details
Retrieves detailed information about a specific question, including supported database types.

- **URL**: `/question/{id}`
- **Method**: `GET`
- **Parameters**:
  - `id` (path): The UUID of the question.

**Response Example:**
```json
{
  "id": "5f06da94-ad81-4241-80b3-4acad7cc6414",
  "questionCode": "SQL099",
  "title": "Find custom referee",
  "content": "HTML content...",
  "questionDetails": [
    {
      "id": "e34ac6a9-ad1d-4efe-a954-b1a043208fb0",
      "typeDatabase": {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Mysql"
      }
    }
  ]
}
```

### 2. Run Query (Dry Run)
Executes a SQL query against the database without submitting it for grading. Used for testing.

- **URL**: `/executor/user`
- **Method**: `POST`
- **Payload**:
```json
{
  "questionId": "c3cce420-fe30-4b07-a021-18cd21c324ee",
  "sql": "SELECT * FROM Student;",
  "typeDatabaseId": "11111111-1111-1111-1111-111111111111"
}
```

**Response (Success):**
```json
{
    "status": 1,
    "result": [
        {
            "col1": "val1",
            "col2": "val2"
        }
    ],
    "typeQuery": "SELECT",
    "timeExec": 1.0
}
```

**Response (Error):**
```json
{
    "status": 0,
    "result": "Error message string (e.g., SQL syntax error)"
}
```

### 3. Submit Solution
Submits a SQL query for grading.

- **URL**: `/executor/submit`
- **Method**: `POST`
- **Payload**:
```json
{
  "questionId": "c3cce420-fe30-4b07-a021-18cd21c324ee",
  "sql": "SELECT * FROM Student;",
  "typeDatabaseId": "11111111-1111-1111-1111-111111111111"
}
```

**Response:**
```json
{
    "status": 1,
    "message": "Submission received" 
}
```
*(Note: Actual success response structure may vary, but `status: 1` indicates success)*

### 4. Get Submission History
Retrieves the submission history for a specific user and question.

- **URL**: `/submit-history/user/{userId}`
- **Method**: `GET`
- **Parameters**:
  - `userId` (path): The UUID of the user.
  - `questionId` (query): The UUID of the question.
  - `page` (query): Page number (0-indexed).
  - `size` (query): Number of items per page.

**Response Example:**
```json
{
  "content": [
    {
      "status": "AC",
      "testPass": 10,
      "totalTest": 10,
      "createdAt": "2025-12-02T17:52:10.098051"
    },
    {
      "status": "WA",
      "testPass": 0,
      "totalTest": 10,
      "createdAt": "2025-12-02T17:50:00.000000"
    }
  ],
  "totalPages": 1,
  "totalElements": 2,
  "size": 2,
  "number": 0,
  "last": true,
  "first": true,
  "numberOfElements": 2,
  "sort": {
    "sorted": false,
    "unsorted": true,
    "empty": true
  }
}
```
### 5. Check Submission Status (Bulk)
Retrieves the submission status for a list of questions.

- **URL**: `/submit-history/check/complete`
- **Method**: `POST`
- **Payload**:
```json
{
  "questionIds": [
    "360518cb-fb15-47bb-9b98-b76e01a39f40",
    "a6bc5583-740c-4ae0-9081-e4a5ecf9a661"
  ],
  "userId": "af39ddb2-8d3a-40f8-8e84-c3bae6e96958"
}
```

**Response Example:**
```json
[
  {
    "completed": "done",
    "questionId": "360518cb-fb15-47bb-9b98-b76e01a39f40",
    "status": "AC"
  },
  {
    "completed": "done",
    "questionId": "a6bc5583-740c-4ae0-9081-e4a5ecf9a661",
    "status": "CE"
  }
]
```
