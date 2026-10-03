from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Event, Participant, Task, HelpRequest, HelpAssignment, ResourceRequest, Handoff
from .utils import generate_anonymous_id, generate_coordinator_token, generate_event_code

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Handoff", description="Live Event Operations System")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={}
    )

@app.get("/create-event", response_class=HTMLResponse)
def create_event_page(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="create_event.html",
    context={}
)

@app.post("/create-event")
def create_event(name: str = Form(...), description: str = Form(""), venue: str = Form(""),
                 date: str = Form(...), start_time: str = Form(...), end_time: str = Form(...),
                 db: Session = Depends(get_db)):
    event_code = generate_event_code()
    while db.query(Event).filter(Event.event_code == event_code).first():
        event_code = generate_event_code()
    coordinator_token = generate_coordinator_token()
    event = Event(name=name, description=description, venue=venue, date=date,
                  start_time=start_time, end_time=end_time, event_code=event_code,
                  coordinator_token=coordinator_token, status="UPCOMING")
    db.add(event); db.commit(); db.refresh(event)
    return RedirectResponse(f"/admin/{event.id}?token={coordinator_token}", status_code=303)

@app.get("/join", response_class=HTMLResponse)
def join_page(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="join_event.html",
    context={}
)

@app.post("/join")
def join_event(event_code: str = Form(...), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_code == event_code.strip().upper()).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    participant = Participant(anonymous_id=generate_anonymous_id(), event_id=event.id, role="VOLUNTEER")
    db.add(participant); db.commit(); db.refresh(participant)
    response = RedirectResponse(f"/event/{event.id}?participant={participant.id}", status_code=303)
    response.set_cookie("participant_id", str(participant.id), httponly=True, max_age=60*60*24*30)
    response.set_cookie("event_id", str(event.id), httponly=True, max_age=60*60*24*30)
    return response

@app.get("/event/{event_id}", response_class=HTMLResponse)
def event_page(request: Request, event_id: int, participant: int | None = None,
               db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    participant_obj = None
    if participant:
        participant_obj = db.query(Participant).filter(
            Participant.id == participant, Participant.event_id == event_id).first()
    tasks = db.query(Task).filter(Task.event_id == event_id).order_by(Task.created_at.desc()).all()
    help_requests = db.query(HelpRequest).filter(HelpRequest.event_id == event_id).order_by(HelpRequest.created_at.desc()).all()
    resources = db.query(ResourceRequest).filter(ResourceRequest.event_id == event_id).order_by(ResourceRequest.created_at.desc()).all()
    handoffs = db.query(Handoff).filter(Handoff.event_id == event_id).order_by(Handoff.created_at.desc()).all()
    return templates.TemplateResponse(
    request=request,
    name="event.html",
    context={
        "event": event,
        "participant": participant_obj,
        "tasks": tasks,
        "help_requests": help_requests,
        "resources": resources,
        "handoffs": handoffs
    }
)

@app.get("/admin/{event_id}", response_class=HTMLResponse)
def admin_dashboard(request: Request, event_id: int, token: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    if token != event.coordinator_token: raise HTTPException(status_code=403, detail="Invalid coordinator token")
    tasks = db.query(Task).filter(Task.event_id == event_id).order_by(Task.created_at.desc()).all()
    help_requests = db.query(HelpRequest).filter(HelpRequest.event_id == event_id).order_by(HelpRequest.created_at.desc()).all()
    resources = db.query(ResourceRequest).filter(ResourceRequest.event_id == event_id).order_by(ResourceRequest.created_at.desc()).all()
    handoffs = db.query(Handoff).filter(Handoff.event_id == event_id).order_by(Handoff.created_at.desc()).all()
    participants = db.query(Participant).filter(Participant.event_id == event_id).all()
    completed = db.query(Task).filter(Task.event_id == event_id, Task.status == "COMPLETED").count()
    pending = db.query(Task).filter(Task.event_id == event_id, Task.status != "COMPLETED").count()
    return templates.TemplateResponse(
    request=request,
    name="admin.html",
    context={
        "event": event,
        "tasks": tasks,
        "help_requests": help_requests,
        "resources": resources,
        "handoffs": handoffs,
        "participants": participants,
        "completed": completed,
        "pending": pending,
        "token": token
    }
)

@app.post("/admin/{event_id}/task")
def create_task(event_id: int, token: str = Form(...), title: str = Form(...),
                description: str = Form(""), location: str = Form(""), priority: str = Form("NORMAL"),
                db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or token != event.coordinator_token: raise HTTPException(status_code=403)
    db.add(Task(title=title, description=description, location=location, priority=priority,
                status="PENDING", event_id=event_id))
    db.commit()
    return RedirectResponse(f"/admin/{event_id}?token={token}", status_code=303)

def get_task_and_participant(task_id, participant_id, db):
    task = db.query(Task).filter(Task.id == task_id).first()
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not task or not participant: raise HTTPException(status_code=404)
    if task.event_id != participant.event_id: raise HTTPException(status_code=403)
    return task, participant

@app.post("/task/{task_id}/claim")
def claim_task(task_id: int, participant_id: int = Form(...), db: Session = Depends(get_db)):
    task, participant = get_task_and_participant(task_id, participant_id, db)
    if task.status == "PENDING":
        task.assigned_to_id = participant.id
        task.status = "CLAIMED"
        db.commit()
    return RedirectResponse(f"/event/{task.event_id}?participant={participant.id}", status_code=303)

@app.post("/task/{task_id}/start")
def start_task(task_id: int, participant_id: int = Form(...), db: Session = Depends(get_db)):
    task, participant = get_task_and_participant(task_id, participant_id, db)
    if task.assigned_to_id != participant_id: raise HTTPException(status_code=403)
    task.status = "IN_PROGRESS"; db.commit()
    return RedirectResponse(f"/event/{task.event_id}?participant={participant_id}", status_code=303)

@app.post("/task/{task_id}/complete")
def complete_task(task_id: int, participant_id: int = Form(...), db: Session = Depends(get_db)):
    task, participant = get_task_and_participant(task_id, participant_id, db)
    if task.assigned_to_id != participant_id: raise HTTPException(status_code=403)
    task.status = "COMPLETED"; db.commit()
    return RedirectResponse(f"/event/{task.event_id}?participant={participant_id}", status_code=303)

@app.post("/event/{event_id}/help")
def create_help_request(event_id: int, participant_id: int = Form(...), title: str = Form(...),
                        description: str = Form(""), location: str = Form(""),
                        priority: str = Form("NORMAL"), required_people: int = Form(1),
                        db: Session = Depends(get_db)):
    participant = db.query(Participant).filter(Participant.id == participant_id, Participant.event_id == event_id).first()
    if not participant: raise HTTPException(status_code=403)
    db.add(HelpRequest(title=title, description=description, location=location,
                       priority=priority, required_people=max(1, required_people),
                       status="OPEN", event_id=event_id, created_by_id=participant_id))
    db.commit()
    return RedirectResponse(f"/event/{event_id}?participant={participant_id}", status_code=303)

@app.post("/help/{request_id}/join")
def join_help_request(request_id: int, participant_id: int = Form(...), db: Session = Depends(get_db)):
    help_request = db.query(HelpRequest).filter(HelpRequest.id == request_id).first()
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not help_request or not participant: raise HTTPException(status_code=404)
    if help_request.event_id != participant.event_id: raise HTTPException(status_code=403)
    already = db.query(HelpAssignment).filter(
        HelpAssignment.request_id == request_id, HelpAssignment.participant_id == participant_id).first()
    if not already:
        db.add(HelpAssignment(request_id=request_id, participant_id=participant_id))
        db.flush()
    count = db.query(HelpAssignment).filter(HelpAssignment.request_id == request_id).count()
    help_request.status = "FULFILLED" if count >= help_request.required_people else "PARTIALLY_FILLED"
    db.commit()
    return RedirectResponse(f"/event/{participant.event_id}?participant={participant.id}", status_code=303)

@app.post("/event/{event_id}/resource")
def create_resource(event_id: int, participant_id: int = Form(...), item: str = Form(...),
                    quantity: int = Form(1), location: str = Form(""), priority: str = Form("NORMAL"),
                    db: Session = Depends(get_db)):
    participant = db.query(Participant).filter(Participant.id == participant_id, Participant.event_id == event_id).first()
    if not participant: raise HTTPException(status_code=403)
    db.add(ResourceRequest(item=item, quantity=max(1, quantity), location=location,
                            priority=priority, status="REQUESTED", event_id=event_id))
    db.commit()
    return RedirectResponse(f"/event/{event_id}?participant={participant_id}", status_code=303)

@app.post("/resource/{resource_id}/status")
def resource_status(resource_id: int, token: str = Form(...), status: str = Form(...),
                    db: Session = Depends(get_db)):
    resource = db.query(ResourceRequest).filter(ResourceRequest.id == resource_id).first()
    if not resource: raise HTTPException(status_code=404)
    event = db.query(Event).filter(Event.id == resource.event_id).first()
    if not event or token != event.coordinator_token: raise HTTPException(status_code=403)
    resource.status = status; db.commit()
    return RedirectResponse(f"/admin/{event.id}?token={token}", status_code=303)

@app.post("/event/{event_id}/handoff")
def create_handoff(event_id: int, participant_id: int = Form(...), what_happened: str = Form(""),
                   remaining: str = Form(""), issues: str = Form(""), next_action: str = Form(""),
                   db: Session = Depends(get_db)):
    participant = db.query(Participant).filter(Participant.id == participant_id, Participant.event_id == event_id).first()
    if not participant: raise HTTPException(status_code=403)
    db.add(Handoff(event_id=event_id, from_participant_id=participant_id,
                   what_happened=what_happened, remaining=remaining,
                   issues=issues, next_action=next_action))
    db.commit()
    return RedirectResponse(f"/event/{event_id}?participant={participant_id}", status_code=303)

@app.post("/admin/{event_id}/status")
def change_event_status(event_id: int, token: str = Form(...), status: str = Form(...),
                        db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or token != event.coordinator_token: raise HTTPException(status_code=403)
    event.status = status; db.commit()
    return RedirectResponse(f"/admin/{event_id}?token={token}", status_code=303)
