import datetime
from flask import jsonify, request
from src import db
from src.models import AttendanceSetting

def get_attendance_settings(decoded_payload=None):
    try:
        # Get the active attendance setting
        setting = AttendanceSetting.query.filter_by(is_active=True).first()
        
        # If no setting exists, return default values
        if not setting:
            return jsonify({
                "setting": {
                    "week_start_day": "Monday",
                    "week_end_day": "Saturday",
                    "start_time": "09:00:00",
                    "end_time": "18:00:00",
                    "daily_working_hours": 8.0
                },
                "status": 1
            }), 200
        
        # Convert time objects to string for JSON
        return jsonify({
            "setting": {
                "attendance_setting_id": setting.attendance_setting_id,
                "week_start_day": setting.week_start_day,
                "week_end_day": setting.week_end_day,
                "start_time": setting.start_time.strftime("%H:%M:%S"),
                "end_time": setting.end_time.strftime("%H:%M:%S"),
                "daily_working_hours": setting.daily_working_hours
            },
            "status": 1
        }), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def save_attendance_settings(decoded_payload=None):
    try:
        data = request.get_json()
        
        # Parse times from HH:MM:SS or HH:MM format
        def parse_time(time_str):
            if not time_str:
                return None
            # Handle both HH:MM and HH:MM:SS
            parts = time_str.split(':')
            if len(parts) == 2:
                hours, minutes = map(int, parts)
                seconds = 0
            else:
                hours, minutes, seconds = map(int, parts)
            return datetime.time(hours, minutes, seconds)
        
        # Deactivate all existing settings first
        AttendanceSetting.query.update({AttendanceSetting.is_active: False})
        
        # Create new setting
        new_setting = AttendanceSetting(
            week_start_day=data.get("week_start_day", "Monday"),
            week_end_day=data.get("week_end_day", "Saturday"),
            start_time=parse_time(data.get("start_time")),
            end_time=parse_time(data.get("end_time")),
            daily_working_hours=data.get("daily_working_hours", 8.0),
            is_active=True
        )
        
        db.session.add(new_setting)
        db.session.commit()
        
        return jsonify({
            "msg": "Attendance settings saved successfully",
            "setting": {
                "attendance_setting_id": new_setting.attendance_setting_id,
                "week_start_day": new_setting.week_start_day,
                "week_end_day": new_setting.week_end_day,
                "start_time": new_setting.start_time.strftime("%H:%M:%S"),
                "end_time": new_setting.end_time.strftime("%H:%M:%S"),
                "daily_working_hours": new_setting.daily_working_hours
            },
            "status": 1
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500