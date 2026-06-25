# Mobile Frontend E2E Checklist

## Scope

This PR connects the React Native Expo app to the BADA backend E2E flow requested by the team.

- Social OAuth login (Google / Kakao / Naver)
- Mobile deep link callback: `bada://auth` or Expo `exp://.../auth`
- Token storage in Expo SecureStore
- `Authorization: Bearer <token>` API calls
- Case creation
- Evidence upload through backend multipart upload
- AI chatbot call with the selected UUID case id

## User Persona For Manual QA

- Persona: worker preparing consultation material from a phone
- Goal: log in, create a case, upload one payslip or image, ask the chatbot what to say first at consultation
- Device: Android emulator or Android phone with Expo Go

## Manual Test Procedure

1. Start the backend or use the deployed API.
   - Local: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
   - Deployed: `https://api.badasoft.com`

2. Start the mobile app.
   - `cd mobile-native`
   - `npm install`
   - `npx expo start -c`
   - Open in Android emulator or Expo Go.

3. Login.
   - Tap `구글로 시작하기`.
   - Confirm that the browser opens the provider OAuth login (Google / Kakao / Naver).
   - Select a Google test account.
   - Confirm that the app returns to BADA and lands on the home screen.

4. Confirm authenticated API calls.
   - The home screen calls `GET /auth/me`.
   - Expected result: the user name or email appears in the greeting.
   - Failure signal: app returns to login or shows an API 401 error.

5. Create a case.
   - Tap `사건 만들기`.
   - Enter workplace name, employer name, start date, wage, and issue type.
   - Save.
   - Expected result: app navigates to the new case detail page.
   - API path: `POST /cases`.

6. Upload evidence.
   - Tap `자료 업로드`.
   - Select a case and an evidence category.
   - Upload a PDF/image from file picker or gallery.
   - Expected result: upload success alert and the uploaded file appears in the session list.
   - API path: `POST /cases/{case_id}/evidences/upload`.

7. Ask the AI chatbot.
   - Open the chatbot from the case detail page.
   - Ask: `상담하러 가면 뭐부터 말하면 좋을까요?`
   - Expected result: chatbot returns a preparation-oriented answer, not a legal judgment.
   - API path: `POST /chat/messages`.

## Network Checks

When debugging, confirm these requests:

- `GET /auth/{provider}/login?redirect_uri=...` (provider = google | kakao | naver)
- `GET /auth/{provider}/callback?code=...&state=...`
- `GET /auth/me` with `Authorization: Bearer <token>`
- `POST /cases` with `Authorization: Bearer <token>`
- `POST /cases/{case_id}/evidences/upload` with `Authorization: Bearer <token>`
- `POST /chat/messages`

## Backend Contract Notes

- Mobile OAuth passes `redirect_uri=bada://auth` or an Expo `exp://.../auth` URL to the backend.
- Backend stores this app return URL inside OAuth `state`.
- After the provider OAuth callback, backend redirects to `return_to?token=<token>`.
- If the callback has no valid app return URL, backend falls back to `APP_BASE_URL/#token=<token>` for web.
- Upload uses backend multipart upload. Backend storage decides local filesystem vs S3 through `STORAGE_MODE` and `S3_BUCKET`.

## Automated Verification

Run from `backend`:

```bash
python -m pytest tests/test_mobile_e2e.py -q
```

Run from `mobile-native`:

```bash
npm exec tsc -- --noEmit
npm exec expo -- export --platform android --no-bytecode --output-dir .expo-export-check
```

Remove `.expo-export-check` after the export smoke test.

## Current Test Account

Use a Google account added to the Google OAuth test users or an account allowed by the production OAuth publishing status.

Do not commit Google/Kakao/Naver OAuth client secrets or personal test account passwords.