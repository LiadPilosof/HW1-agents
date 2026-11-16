# מטלה 1: מערכות בינה מלאכותית — צ׳אט אישי עם מעריך תשובות ולולאת שיפור
## חלק א׳ (Actor) + חלק ב׳ (Critic / Response Evaluator & Pydantic Structured Output)

פרויקט זה מממש את **חלק א׳** ואת **חלק ב׳** של מטלה 1 בקורס "מערכות בינה מלאכותית" (ד"ר פאול אברהמי), בהתבסס על חומר הלימוד של הרצאה 2 (שקפים 19–21) ומחברות המעבדה הנלוות (Labs 1–4).

---

## 1. ארכיטקטורת המערכת ומבנה הפרויקט (Modular Structure)

הקוד בנוי במבנה מודולרי מוקפד, שבו רכיב היצירה (Actor) ורכיב ההערכה (Critic) מופרדים לחלוטין לקראת חיבורם בלולאת השיפור (Part C):

```text
HW1/
├── data/
│   ├── linkedin_profile.txt       # מקור רקע 1: פרופיל מקצועי מפורט (פרופיל לדוגמה)
│   └── personal_summary.txt       # מקור רקע 2: סיכום אישי ומקצועי כחצי עמוד (פרופיל לדוגמה)
├── src/
│   ├── __init__.py
│   ├── schema.py                  # מודל Pydantic Structured Output בשם Evaluation (חלק ב׳)
│   ├── config.py                  # הגדרות סביבה (.env), מודלים (MODEL_NAME, CRITIC_MODEL_NAME)
│   ├── prompts.py                 # הנחיות ה-Actor וה-Critic (SYSTEM_EVALUATOR, USER_EVALUATOR)
│   ├── actor.py                   # יוצר התשובה (Actor), ניהול היסטוריית השיחה וקריאה ל-LLM
│   ├── evaluator.py               # מעריך התשובות (Critic), אכיפת סכמה וטיפול בשגיאות טכניות
│   └── logger.py                  # ניהול יומן בדיקה נפרד (inspection_log.json)
├── logs/
│   └── inspection_log.json        # יומן מעקב נפרד עבור טיוטות, החלטות מעריך ושגיאות טכניות
├── tests/
│   ├── test_part_a.py             # בדיקות יחידה ואינטגרציה ל-Actor (חלק א׳)
│   └── test_evaluator.py          # בדיקות יחידה ואינטגרציה ל-Critic (חלק ב׳)
├── assets/
│   ├── bot_avatar.svg             # אוואטר שטוח וקטורי לדמות
│   └── user_avatar.svg            # אוואטר שטוח וקטורי למשתמש
├── app.py                         # ממשק צ'אט מקומי בעברית מבוסס Gradio
├── requirements.txt               # תלויות הפרויקט (openai, pydantic, gradio, python-dotenv)
├── .env.example                   # קובץ דוגמה להגדרת משתני סביבה
├── .gitignore                     # החרגת מפתחות סודיים, מטמון וסביבה וירטואלית
└── README.md                      # הוראות התקנה, הגדרה והרצה
```

---

## 2. מודלי השפה (LLMs) וספריית הלקוח

- **ספריית הלקוח**: `OpenAI` Python SDK הרשמי (תמיכה מובנית ב-Structured Outputs).
- **מודל ה-Actor**: `gpt-4o-mini` (מוגדר ב-`MODEL_NAME` בקובץ `.env`).
- **מודל ה-Critic**: `gpt-4o-mini` (מוגדר ב-`CRITIC_MODEL_NAME` בקובץ `.env`, ניתן להגדרה עצמאית).

---

## 3. סכמת ההערכה המובנית (Pydantic Schema: `Evaluation`)

מוגדרת בקובץ `src/schema.py` בדיוק לפי דרישות המטלה:
```python
from pydantic import BaseModel, Field

class Evaluation(BaseModel):
    is_acceptable: bool = Field(description="החלטה האם התשובה עומדת בכל הקריטריונים (True) או נדחית (False).")
    feedback: str = Field(description="נימוק קצר. במקרה של דחייה, פירוט הבעיה הספציפית והנחיה מעשית לתיקון.")
```

ההחלטה להמשך התהליך מבוססת באופן בלעדי על השדה הבוליאני `is_acceptable` המאומת, ולא על חיפוש מילים בטקסט חופשי.

---

## 4. הנחיות המעריך — קריטריוני החלטה (`SYSTEM_EVALUATOR`)

מוגדר ב-`src/prompts.py` ואוכף 4 קריטריונים מחייבים:
1. **א. ביסוס במקורות (Source Grounding):** כל העובדות נתמכות במפורש במקורות הרקע. אין הישגים, מעסיקים או עובדות שהומצאו.
2. **ב. מענה לשאלה (Answering the Question):** התשובה מתייחסת ישירות לבקשת המשתמש ולהקשר השיחה.
3. **ג. טיפול במידע חסר (Handling Missing Information):** כאשר אין בסיס עובדתי במקורות, תשובה שמבהירה בצדק ובמפורש שחסר מידע מאושרת (`is_acceptable=True`). תשובה שמנחשת או ממציאה נדחית.
4. **ד. בהירות וסגנון (Clarity & Style):** תשובה ברורה, עניינית, מנומסת ובגוף ראשון.

הודעת הבדיקה (`build_user_evaluator_prompt`) מעבירה למעריך בכל פנייה:
- את שאלת המשתמש הנוכחית
- את התשובה המועמדת
- את מקורות הרקע המלאים (`linkedin_profile.txt` ו-`personal_summary.txt`)
- את היסטוריית השיחה הרלוונטית

---

## 5. טיפול בשגיאות טכניות ויומן בדיקה (Inspection Log)

- **מניעת כשל סכמה כאישור תוכן:**
  במקרה של כשל קריאה לרשת, שגיאת פענוח JSON, או אי-התאמה לסכמת Pydantic (`ValidationError`), נזרקת שגיאה מסוג `TechnicalEvaluationError`. המערכת מתעדת ביומן הבדיקה סטטוס `TECHNICAL_ERROR` עם ציון מפורש שההערכה לא הושלמה (`is_acceptable: None`), ועוצרת את הטיפול ללא מתן אישור שגוי.
- **יומן הבדיקה (`logs/inspection_log.json`):**
  מתעד בנפרד מממשק המשתמש כל טיוטה, את החלטת המעריך (`is_acceptable`), ואת המשוב המנומק (`feedback`).

---

## 6. הוראות התקנה והרצה

### התקנת תלויות:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### הגדרת מפתחות סביבה (.env):
```bash
cp .env.example .env
# ערוך את .env והגדר OPENAI_API_KEY
```

### הרצת הבדיקות האוטומטיות:
```bash
# בדיקות חלק א׳ (Actor)
python tests/test_part_a.py

# בדיקות חלק ב׳ (Critic / Evaluator)
python tests/test_evaluator.py
```

### הפעלת הצ׳אט:
```bash
python app.py
```
והממשק יהיה זמין בדפדפן בכתובת: `http://127.0.0.1:7860`.
