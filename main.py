import uvicorn
from fastapi import FastAPI
from connection import spreadsheet
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo
from env_manager import HOST

IST = ZoneInfo("Asia/Kolkata")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[HOST],   # later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_sheet(name: str):
    return spreadsheet.worksheet(name)

def format_date(date_value=None):
    if date_value is None:
        dt = datetime.now(IST)

    elif isinstance(date_value, datetime):
        dt = date_value.astimezone(IST)

    else:
        dt = datetime.strptime(date_value, "%Y-%m-%d").replace(tzinfo=IST)

    return dt.strftime("%d %b %Y")

def get_next_adm_no(counter_sheet):
    current = int(counter_sheet.acell("B1").value)
    next_adm = current + 1

    return next_adm

# New Admission Adding
@app.post("/add-student")
def add_student(data: dict):

    sheet = get_sheet("Students")
    counter_sheet = get_sheet("Counter")
    
    # ---- Generate Admission No ----
    adm_no = get_next_adm_no(counter_sheet)
    adm_date = format_date(data.get("date"))

    total_paid = 0

    std_data_row = [
        adm_no,
        data.get("name"),
        adm_date,
        data.get("school"),
        data.get("address"),
        data.get("phone"),
        data.get("class"),
        data.get("division"),
        data.get("medium"),
        data.get("nmms"),
        int(data.get("total")),
        int(data.get("reduction")),
        int(total_paid)
    ]

    # ---------- FAST NEXT ROW (counter based) ----------
    student_row_counter = int(counter_sheet.acell("B3").value)
    next_student_row = student_row_counter + 1

    try:        
        spreadsheet.values_batch_update({
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": f"Students!A{next_student_row}:M{next_student_row}",
                    "values": [std_data_row],
                },
                {
                    "range": "Counter!B1",   # adm counter
                    "values": [[adm_no]],
                },
                {
                    "range": "Counter!B3",   # student counter
                    "values": [[next_student_row]],
                },
            ],
        })
    except Exception as e:
        print(e)
        return {"success": False, "message": "Failed to add student."}
    
    return {"success": True, "message": "New Student Added"}

# Get all students
@app.get("/students")
def get_students():
    sheet = get_sheet("Students")

    rows = sheet.get("A3:N")

    students = []

    for i, r in enumerate(rows):
        if not r or not r[0]:
            continue

        students.append({
            "row_idx": i + 3,
            "adm_no": r[0],
            "std_name": r[1],
            "adm_date": r[2],
            "school": r[3],
            "address": r[4],
            "mobile": r[5],
            "std_class": r[6],
            "medium": r[8],
            "nmms": r[9],
            "total_fee": r[10],
            "fee_reduction": r[11],
            "prev_paid": r[12],
            "balance": r[13],
        })

    return students

def generate_bill(counter_sheet):
    current = int(counter_sheet.acell("B2").value)
    next_no = current + 1

    year = datetime.now().year
    bill_no = f"BILL-{year}-{next_no}"

    return bill_no, next_no
    
# add fee logs
@app.post("/pay-fee")
def pay_fee(data: dict):

    student = data.get("student", {})

    admno = student.get("adm_no")
    name = student.get("std_name")
    std_class = student.get("std_class")
    medium = student.get("medium")
    total_fee = student.get("total_fee")
    fee_reduction = student.get("fee_reduction")
    prev_paid = student.get("prev_paid")

    paid_now = data.get("paying_amount", 0)
    
    payment_method = data.get("payment_method", "")
    
    next_due = data.get("next_due", "")
    due_date = ""
    
    if not student or paid_now <= 0 or not payment_method:
        return {"success": False, "msg": "Invalid data"}

    counter_sheet = get_sheet("Counter")
    
    # ---- generate bill ----
    bill_no, counter_bill_no = generate_bill(counter_sheet)
    bill_date = format_date()
    
    if next_due:
        due_date = format_date(next_due) 
    
    std_total_paid = int(prev_paid) + int(paid_now)
    
    new_fee_balance = int(total_fee) - int(fee_reduction) - int(std_total_paid)
    
    # ---------- FAST NEXT ROW (counter based) ----------
    fee_row_counter = int(counter_sheet.acell("B4").value)
    next_fee_row = fee_row_counter + 1
    
    student_row = int(student.get("row_idx"))
    
    fee_log_row = [
        bill_date,
        bill_no,
        "2026-2027",
        admno,
        name,
        std_class,
        medium,
        total_fee,
        prev_paid,
        paid_now,
        payment_method,
        new_fee_balance,
        due_date
    ]

    try:
        
        spreadsheet.values_batch_update({
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": f"FeeLogs!A{next_fee_row}:M{next_fee_row}",
                    "values": [fee_log_row],
                },
                {
                    "range": f"Students!M{student_row}",
                    "values": [[std_total_paid]],
                },
                {
                    "range": "Counter!B2",   # bill counter
                    "values": [[counter_bill_no]],
                },
                {
                    "range": "Counter!B4",   # fee row counter
                    "values": [[next_fee_row]],
                },
            ],
        })
        
    except Exception as e:
        print(e)
        return {"success": False, "message": "Failed to add fee data."}
    
    return {
        "success": True,
        "message": "Fee Updated",
        "receipt": {
            "bill_date": bill_date,
            "bill_no": bill_no,
            "academic_year": "2026-2027",
            "admno": admno,
            "name": name,
            "std_class": std_class,
            "medium": medium,
            "total_fee": total_fee,
            "prev_paid": prev_paid,
            "paid_now": paid_now,
            "payment_method": payment_method,
            "balance": new_fee_balance,
            "due_date": due_date
        }
    }
    
# Get all fee logs
@app.get("/feelogs")
def get_fee_logs():
    sheet = get_sheet("FeeLogs")

    rows = sheet.get("A3:M")

    fee_logs = []

    for i, r in enumerate(rows):
        if not r or not r[0]:
            continue
        
        due_date = r[12] if len(r) == 13 else ""

        fee_logs.append({
            "row_idx": i + 3,
            "bill_date": r[0],
            "bill_no": r[1],
            "academic_year": r[2],
            "adm_no": r[3],
            "std_name": r[4],
            "std_class": r[5],
            "medium": r[6],
            "total_fee": r[7],
            "prev_paid": r[8],
            "paid_amt": r[9],
            "payment_method": r[10],
            "balance": r[11],
            "due_date": due_date
        })

    return fee_logs