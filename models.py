from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime
import json

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    full_name = Column(String)
    role = Column(String, default="operator")
    
    @property
    def role_list(self):
        return self.role.split(",") if self.role else ["operator"]
    
    @property
    def primary_role(self):
        if "admin" in self.role_list:
            return "admin"
        elif "mechanic" in self.role_list:
            return "mechanic"
        return "operator"

class Toolbox(Base):
    __tablename__ = "toolboxes"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    tools_json = Column(Text, default="[]")
    
    def get_tools(self):
        return json.loads(self.tools_json)
    
    def set_tools(self, tools):
        self.tools_json = json.dumps(tools, ensure_ascii=False)

class ToolCheck(Base):
    __tablename__ = "tool_checks"
    id = Column(Integer, primary_key=True)
    toolbox_id = Column(Integer, ForeignKey("toolboxes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    tool_name = Column(String)
    is_present = Column(Boolean)
    comment = Column(String, default="")
    photo_path = Column(String, nullable=True)

class BoxStatus(Base):
    __tablename__ = "box_statuses"
    id = Column(Integer, primary_key=True)
    toolbox_id = Column(Integer, ForeignKey("toolboxes.id"), unique=True)
    last_check_time = Column(DateTime, nullable=True)
    last_check_user = Column(Integer, nullable=True)
    last_user = Column(String, nullable=True)
    is_complete = Column(Boolean, default=True)
