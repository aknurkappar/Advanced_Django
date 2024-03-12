# Job site
from typing import Annotated

import punq
# job -> title, salary, time, experience, employer(many to one)(1), skills (many to many)(2)
# employer -> name, location, jobs (one to many)(1)
# candidate -> name, age, applications(one to many)(3), resumes(one to many)(4)
# skill -> title, jobs(2), applications(many to many)(5)
# application -> candidate_id, job_id, date, status, candidate(many to one)(3)
# resume -> candidates_id, skills(many to many)(5), candidate(many to one)(4), experience, education

# try yield finally

# Requirements:
# Use all topics in syllabus
# Minimum 15 api handlers (post, get) // 17
# Use DI as class, as function // 0 - callable and with methods
# 6 Models, 4 relationships // 6 models, 5 relationships
# Write min 10 tests // 0


from fastapi import FastAPI, Depends
import database as db
import models
import schemas
from repository import BasicRepository, JobBasicRepository

app = FastAPI()


class BasicDependency:
    def __init__(self, repo: BasicRepository):
        self.repo = repo

    def __call__(self, id: int) -> schemas.ReturnType:
        return self.repo

    def get_all(self) -> list[schemas.ReturnType]:
        return self.repo.get_all()

    def add(self, data: schemas.CreateType):
        return self.repo.add(data)


def get_basic_container(repository: type[BasicRepository]) -> punq.Container:
    container = punq.Container()
    container.register(BasicRepository, repository, instance=repository(session=db.session))
    container.register(BasicDependency)
    return container


@app.get('/employers')
def get_employers():
    db_employers = db.session.execute().scalars().all()
    employers = [schemas.Employer.model_validate(employer) for employer in db_employers]
    return employers


@app.post('/employers')
def add_employer(employer: schemas.CreateEmployer):
    db.session.add(models.Employer(**employer.model_dump()))
    db.session.commit()
    db.session.close()
    return f"{employer.name} was added"


@app.get('/jobs')
def get_jobs(jobs: Annotated[list[schemas.Job], Depends(get_basic_container(JobBasicRepository).resolve(BasicDependency).get_all)]):
    if jobs is None:
        return 'No jobs'
    return jobs


@app.post('/jobs')
def add_job(job: Annotated[schemas.CreateJob, Depends(get_basic_container(JobBasicRepository).resolve(BasicDependency).add)]):
    if job is None:
        return 'Try again'
    return job


@app.post('/candidates')
def add_candidate(candidate: schemas.CreateCandidate):
    db.session.add(models.Candidate(**candidate.model_dump()))
    db.session.commit()
    db.session.close()
    return f"{candidate.name} was added"


@app.get('/candidates')
def get_candidate_by_id(id: int):
    db_candidate = db.session.get(models.Candidate, id)
    candidate = schemas.Candidate.model_validate(db_candidate)
    return candidate


@app.post('/skills')
def add_skill(skill: schemas.CreateSkill):
    db.session.add(models.Skill(**skill.model_dump()))
    db.session.commit()
    db.session.close()
    return f"{skill.title} was added"


@app.get('/skills')
def get_skills():
    db_skills = db.session.execute().scalars().all()
    skills = [schemas.Skill.model_validate(skill) for skill in db_skills]
    return skills


@app.get('/skills/{title}')
def get_skill_by_title(title: str):
    db_skill = db.session.query(models.Skill).filter(models.Skill.title == title).first()
    skill = schemas.Skill.model_validate(db_skill)
    return skill


@app.post('/candidates/resumes')
def add_resume_to_candidate(resume: schemas.CreateResume):
    db_candidate = db.session.get(models.Candidate, resume.candidate_id)
    candidate = schemas.Candidate.model_validate(db_candidate)

    db.session.add(models.Resume(**resume.model_dump()))
    db.session.commit()
    db.session.close()
    return f"New resume was added to candidate: {candidate.name}"


@app.get('/candidates/resumes')
def get_candidate_resumes(candidate_id: int):
    db_candidate = db.session.get(models.Candidate, candidate_id)
    candidate = schemas.Candidate.model_validate(db_candidate)
    db_resumes = db_candidate.resumes
    resumes = [schemas.Resume.model_validate(resume) for resume in db_resumes]
    return f"{candidate.name}'s resumes: {resumes}"


@app.post('/candidates/applications')
def add_application_to_candidate(application: schemas.CreateApplication):
    db.session.add(models.Application(**application.model_dump()))

    db_candidate = db.session.get(models.Candidate, application.candidate_id)
    db_job = db.session.get(models.Job, application.job_id)
    db_resume = db.session.get(models.Resume, application.resume_id)

    candidate = schemas.Candidate.model_validate(db_candidate)
    job = schemas.Job.model_validate(db_job)
    resume = schemas.Resume.model_validate(db_resume)

    db.session.commit()
    db.session.close()
    return f"{candidate.name} applied to the job: {job.title} with resume {resume.title}"


@app.get('/candidates/applications')
def get_candidate_skills(candidate_id: int):
    db_candidate = db.session.get(models.Candidate, candidate_id)
    candidate = schemas.Candidate.model_validate(db_candidate)
    db_applications = db_candidate.applications
    applications = [schemas.Application.model_validate(application) for application in db_applications]
    return f"Jobs that is {candidate.name} applied: {applications}"


@app.post('/jobs/skills')
def add_skill_to_job(job_id: int, skill_title: str):
    db_job = db.session.get(models.Job, job_id)
    db_skill = db.session.query(models.Skill).filter(models.Skill.title == skill_title).first()
    db_skill.jobs.append(db_job)
    db_job.skills.append(db_skill)
    job = schemas.Job.model_validate(db_job)
    db.session.commit()
    db.session.close()
    return f"{skill_title} was added to candidate: {job.title}"


@app.get('/jobs/skills')
def get_job_skills(job_id: int):
    db_job = db.session.get(models.Job, job_id)
    job = schemas.Job.model_validate(db_job)
    db_skills = db_job.skills
    skills = [schemas.Skill.model_validate(skill) for skill in db_skills]
    return f"Skills that is {job.title} required: {skills}"


@app.get('/jobs/applications')
def get_job_applications(job_id: int):
    db_job = db.session.get(models.Job, job_id)
    db_applications = db_job.applications
    applications = [schemas.Application.model_validate(application) for application in db_applications]
    return applications


@app.put('/applications')
def get_job_applications(application_id: int, status: str):
    db_applications = db.session.get(models.Application, application_id)
    setattr(db_applications, 'status', status)
    application = schemas.Application.model_validate(db_applications)
    db.session.commit()
    db.session.close()
    return application
