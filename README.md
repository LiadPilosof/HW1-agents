# מטלה 1: מערכות בינה מלאכותית, צ׳אט אישי עם מעריך תשובות

הפרויקט מממש את **חלק א׳** (מידע רקע ויוצר התשובה) ואת **חלק ב׳** (מעריך תשובות ופלט מובנה) של המטלה.
לולאת התיקון (חלק ג׳) אינה ממומשת: לכל שאלה מופקת טיוטה אחת ונבדקת פעם אחת.

## זרימת הטיפול בשאלה

1. **יוצר התשובה (Actor)** מקבל את מקורות הרקע (בהודעת המערכת), את היסטוריית השיחה ואת השאלה, ומפיק טיוטה.
2. **מעריך התשובות (Critic)** מקבל את השאלה, הטיוטה, היסטוריית השיחה ושני מקורות הרקע, ומחזיר פלט מובנה שמאומת מול מודל `Evaluation`.
3. ההחלטה נשענת רק על השדה הבוליאני `is_acceptable` לאחר האימות:
   - **אושר:** התשובה מוצגת בצ׳אט ונכנסת להיסטוריה שמשמשת לשאלות המשך.
   - **נדחה:** הטיוטה אינה מוצגת. המשתמש מקבל הודעה שהתשובה לא אושרה.
   - **שגיאה טכנית** (כשל בקריאה למודל, פלט שאינו JSON, שדה חסר או מסוג שגוי): הטיפול בשאלה נעצר עם הודעה ברורה. כשל אימות לעולם אינו נחשב אישור.
4. כל שאלה נרשמת כרשומה אחת ב-`logs/inspection_log.json`, בנפרד מהצ׳אט.

## מבנה הפרויקט

```text
HW1/
├── app.py                  # ממשק Gradio בעברית
├── src/
│   ├── config.py           # נתיבים, שמות מודלים, טעינת מקורות, לקוח OpenAI
│   ├── prompts.py          # הנחיות היוצר (System Prompt) והמעריך (Evaluator System / User)
│   ├── schema.py           # מודל Pydantic בשם Evaluation (is_acceptable: bool, feedback: str)
│   ├── actor.py            # יוצר התשובה
│   ├── evaluator.py        # מעריך התשובות; כל כשל הופך ל-TechnicalEvaluationError
│   ├── pipeline.py         # טיפול בשאלה אחת: טיוטה, הערכה, רישום ביומן
│   ├── theme.py            # מערכת העיצוב: פלטה לבהיר/כהה, ערכת Gradio ו-CSS
│   └── logger.py           # יומן הבדיקה (JSON)
├── data/
│   ├── linkedin_profile.txt   # פרופיל LinkedIn (פרופיל לדוגמה)
│   └── personal_summary.txt   # סיכום אישי בהיקף כחצי עמוד (פרופיל לדוגמה)
├── tests/                  # בדיקות pytest (ללא רשת) + בדיקות חיות אופציונליות
├── logs/inspection_log.json
├── requirements.txt / requirements-dev.txt
└── .env.example
```

## מודלים

| תפקיד | משתנה סביבה | בניסוי |
|---|---|---|
| יוצר התשובה (Actor) | `MODEL_NAME` | `gpt-5.4-mini` |
| מעריך התשובות (Critic) | `CRITIC_MODEL_NAME` (ברירת מחדל: `MODEL_NAME`) | `gpt-5.4-mini` |

שני התפקידים משתמשים בקריאות ובהנחיות נפרדות. המעריך משתמש ב-Structured Outputs של OpenAI (`chat.completions.parse`), והתוצאה מאומתת שוב מול `Evaluation` במצב strict.

## התקנה והרצה

נבדק עם Python 3.14 (נדרש 3.10 ומעלה).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # כולל את requirements.txt + pytest, ruff

cp .env.example .env                  # והגדירו OPENAI_API_KEY

python app.py                         # http://127.0.0.1:7860
```

## בדיקות

```bash
pytest                                # 59 בדיקות, ללא קריאות רשת וללא כתיבה ליומן האמיתי
RUN_LIVE_TESTS=1 pytest -m live       # 3 בדיקות מול המודל המוגדר (נרשמות ביומן)
ruff check . && ruff format --check .
pyright                               # npm install -g pyright
```

## יומן הבדיקה

כל רשומה כוללת: `session_id`, `turn_index`, `question`, `status` (`APPROVED` / `REJECTED` / `TECHNICAL_ERROR`), שמות המודלים, `candidate_response` (הטיוטה), `evaluation` (`is_acceptable` + `feedback`), `evaluation_completed`, `technical_error` (השלב והסיבה) ו-`displayed_response`.
בשגיאה טכנית `evaluation` הוא `null` ו-`evaluation_completed` הוא `false`, כלומר לא נרשמת החלטת תוכן שלא התקבלה.

## בדיקה ידנית של תשובות שאושרו (חלק ב׳)

אימות Pydantic בודק מבנה וסוגי נתונים בלבד, ולא את נכונות ההחלטה. שתי תשובות שאושרו בהרצה החיה הושוו ידנית למקורות:

| שאלה | התשובה שאושרה | הפרט במקור | תואם |
|---|---|---|---|
| באיזה מוסד עשית את התואר השני שלך? | "עשיתי את התואר השני שלי במדעי המחשב בטכניון – מכון טכנולוגי לישראל." | `linkedin_profile.txt`, השכלה 1: "תואר שני (M.Sc.) במדעי המחשב ... הטכניון - מכון טכנולוגי לישראל" | כן |
| ובאיזה ממוצע סיימת אותו? (שאלת המשך) | "סיימתי את התואר השני עם ממוצע 94." | `linkedin_profile.txt`, השכלה 1: "ממוצע ציונים: 94" | כן; ההקשר "אותו" נפתר נכון מהתשובה הקודמת |
