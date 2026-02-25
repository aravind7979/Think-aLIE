# Think-aLIE - AI Language Intelligence Engine

A ChatGPT-like web application with Supabase authentication and database.

## Features

- 🔐 Supabase Authentication (Signup/Login)
- 💬 Multiple Chat Sessions per User
- 🤖 Gemini AI Integration
- 🎨 Modern ChatGPT-like UI
- 📱 Responsive Design

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/CSS/JavaScript
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth
- **AI**: Google Gemini API
- **Deployment**: Railway (Backend), Vercel (Frontend)

## Setup

### Prerequisites

- Python 3.11+
- Supabase account
- Google Gemini API key

### Environment Variables

Create a `.env` file in the backend directory:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
GEMINI_API_KEY=your_gemini_api_key
```

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the backend:
   ```bash
   uvicorn backend.app:app --reload
   ```

### Deployment

- **Backend**: Deploy to Railway (requirements.txt in root)
- **Frontend**: Deploy to Vercel
- Update `home.html` API_URL with your Railway domain

## Database Schema

Create these tables in Supabase:

### chats

```sql
CREATE TABLE chats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  title TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### messages

```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  role TEXT NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Endpoints

- `POST /auth/signup` - User registration
- `POST /auth/login` - User login
- `GET /chats` - List user chats
- `POST /chats` - Create new chat
- `GET /chats/{chat_id}/messages` - Get chat messages
- `POST /chats/{chat_id}/message` - Send message

## License

MIT
