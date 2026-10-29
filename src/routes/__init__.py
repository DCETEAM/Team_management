from src.routes.auth_route import auth_bp
from src.routes.admin_route import admin_bp
from src.routes.worker_route import worker_bp
from src.routes.client_route import client_bp
from src.routes.task_status_route import task_status_bp
from src.routes.project_route import project_bp
from src.routes.project_allocation_route import project_allocation_bp
from src.routes.task_route import task_bp
from src.routes.sub_task_route import sub_task_bp
from src.routes.task_comment_route import task_comment_bp
from src.routes.task_attachment_route import task_attachment_bp
from src.routes.meeting_route import meeting_bp
from src.routes.meeting_message_route import meeting_message_bp
from src.routes.leave_request_route import leave_request_bp
from src.routes.activity_log_route import activity_log_bp
from src.routes.project_group_route import project_group_bp
from src.routes.project_member_route import project_member_bp
from src.routes.project_task_route import project_task_bp
from src.routes.project_excel_route import project_excel_bp
from src.routes.sprint_route import sprint_bp
from src.routes.task_status_history_route import task_status_history_bp
from src.routes.attendance_status_route import attendance_status_bp
from src.routes.attendance_setting_route import attendance_setting_bp
from src.routes.profile_route import profile_bp
from src.routes.monitor_route import monitor_bp

ALL_BLUEPRINTS = (
    auth_bp,
    admin_bp,
    worker_bp,
    client_bp,
    task_status_bp,
    project_bp,
    project_allocation_bp,
    task_bp,
    sub_task_bp,
    task_comment_bp,
    task_attachment_bp,
    meeting_bp,
    meeting_message_bp,
    leave_request_bp,
    activity_log_bp,
    project_group_bp,
    project_member_bp,
    project_task_bp,
    project_excel_bp,
    sprint_bp,
    task_status_history_bp,
    attendance_status_bp,
    attendance_setting_bp,
    profile_bp,
    monitor_bp,
)


def init_routes(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
