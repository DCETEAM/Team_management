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


def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(task_status_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(project_allocation_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(sub_task_bp)
    app.register_blueprint(task_comment_bp)
    app.register_blueprint(task_attachment_bp)
    app.register_blueprint(meeting_bp)
    app.register_blueprint(meeting_message_bp)
    app.register_blueprint(leave_request_bp)
    app.register_blueprint(activity_log_bp)
    app.register_blueprint(project_group_bp)
    app.register_blueprint(project_member_bp)
    app.register_blueprint(project_task_bp)
    app.register_blueprint(project_excel_bp)
    app.register_blueprint(sprint_bp)
    app.register_blueprint(task_status_history_bp)
    app.register_blueprint(attendance_status_bp)
    app.register_blueprint(attendance_setting_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(monitor_bp)


