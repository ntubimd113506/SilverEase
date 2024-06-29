from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore    

class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOBSTORES  = {'default':SQLAlchemyJobStore(url=f"sqlite:///flaskapp/services/scheduler/jobstore/scheduer.db")}