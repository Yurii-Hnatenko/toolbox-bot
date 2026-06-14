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
    role = Column(String, default="operator")  # "operator,mechanic,admin" або "operator,mechanic"
    last_version = Column(String, default="1.0.0")  # Версія бота для відстеження оновлень
    
    @property
    def role_list(self):
        """Повертає список ролей користувача"""
        return self.role.split(",") if self.role else ["operator"]
    
    @property
    def primary_role(self):
        """Головна роль для меню (пріоритет: admin > mechanic > operator)"""
        if "admin" in self.role_list:
            return "admin"
        elif "mechanic" in self.role_list:
            return "mechanic"
        return "operator"
    
    def has_role(self, role_name):
        """Перевіряє, чи має користувач вказану роль"""
        return role_name in self.role_list
    
    def add_role(self, role_name):
        """Додає роль користувачу"""
        if not self.has_role(role_name):
            roles = self.role_list
            roles.append(role_name)
            self.role = ",".join(roles)
    
    def remove_role(self, role_name):
        """Видаляє роль у користувача"""
        if self.has_role(role_name):
            roles = [r for r in self.role_list if r != role_name]
            self.role = ",".join(roles) if roles else "operator"


class Toolbox(Base):
    __tablename__ = "toolboxes"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    tools_json = Column(Text, default="[]")
    
    def get_tools(self):
        """Повертає список інструментів у ящику"""
        return json.loads(self.tools_json)
    
    def set_tools(self, tools):
        """Зберігає список інструментів у ящику"""
        self.tools_json = json.dumps(tools, ensure_ascii=False)


class ToolImage(Base):
    __tablename__ = "tool_images"
    id = Column(Integer, primary_key=True)
    toolbox_id = Column(Integer, ForeignKey("toolboxes.id"))
    tool_name = Column(String)
    photo_path = Column(String)
    uploaded_by = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


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