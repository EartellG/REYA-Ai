"""
REYA-AI - Advanced Feature Implementations
This module contains implementations for advanced AI assistant features
that can be integrated into the existing REYA-AI codebase.
"""

import os
import json
import datetime
import threading
import re
from typing import Dict, List, Any, Optional, Tuple, Callable
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("reya.log"), logging.StreamHandler()]
)
logger = logging.getLogger("REYA-AI")

# -------------------------------------------------
# 1. Contextual Memory System
# -------------------------------------------------

class ContextualMemory:
    def __init__(self, memory_file: str = "memory/user_context.json"):
        self.memory_file = memory_file
        self.history = self._load_memory()
        self._ensure_memory_structure()

    # keep this for backward-compat (some code calls update_context)
    def update_context(self, *args, **kwargs):
        return self.remember(*args, **kwargs)

    # ✅ Return a LIST OF DICTS (what llm_interface expects)
    def get_context(self) -> List[Dict[str, str]]:
        """
        Return the last 5 conversation turns as a list of:
        { "user_input": str, "assistant_response": str, ... }
        """
        conversations = self.history.get("conversations", [])
        return conversations[-5:]

    def _ensure_memory_structure(self):
        if "conversations" not in self.history:
            self.history["conversations"] = []
        if "preferences" not in self.history:
            self.history["preferences"] = {}
        if "entities" not in self.history:
            self.history["entities"] = {}
        if "frequent_topics" not in self.history:
            self.history["frequent_topics"] = {}
        if "language_progress" not in self.history:
            self.history["language_progress"] = {
                "Japanese": {"vocab_known": [], "lessons_completed": [], "daily_streak": 0},
                "Mandarin": {"vocab_known": [], "lessons_completed": [], "daily_streak": 0},
            }

    # ✅ Safer UTF-8 load, creates directory if missing
    def _load_memory(self) -> Dict:
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            return {}
        except Exception as e:
            print(f"Error loading memory: {e}")
            return {}

    # ✅ UTF-8 save; keep non-ASCII; pretty
    def save(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def remember(self, user_input, assistant_response):
        self.history["conversations"].append(
            {
                "user_input": user_input,
                "assistant_response": assistant_response,
                "timestamp": datetime.datetime.now().isoformat(),
                "context": {},
            }
        )
        self.save()

    # 🔁 Alias for callers that use add_conversation()
    def add_conversation(self, user_input, assistant_response):
        return self.remember(user_input, assistant_response)

    def get_recent_conversations(self, count=5):
        return self.history["conversations"][-count:]

    # ✅ NEW METHODS for language learning (with guards)
    def _ensure_language(self, language: str):
        lp = self.history.setdefault("language_progress", {})
        if language not in lp:
            lp[language] = {"vocab_known": [], "lessons_completed": [], "daily_streak": 0}

    def add_vocab(self, language: str, words: List[str]):
        self._ensure_language(language)
        known = self.history["language_progress"][language]["vocab_known"]
        for word in words:
            if word not in known:
                known.append(word)
        self.save()

    def get_vocab(self, language: str) -> List[str]:
        self._ensure_language(language)
        return self.history["language_progress"][language]["vocab_known"]

    def mark_lesson_completed(self, language: str, lesson_id: str):
        self._ensure_language(language)
        lessons = self.history["language_progress"][language]["lessons_completed"]
        if lesson_id not in lessons:
            lessons.append(lesson_id)
        self.save()

    def increment_streak(self, language: str):
        self._ensure_language(language)
        self.history["language_progress"][language]["daily_streak"] += 1
        self.save()

    def get_streak(self, language: str) -> int:
        self._ensure_language(language)
        return self.history["language_progress"][language]["daily_streak"]

    # 🧭 Handy snapshot for “Resume where I left off” banner
    def get_language_snapshot(self, language: str) -> Dict[str, Any]:
        self._ensure_language(language)
        lp = self.history["language_progress"][language]
        return {
            "language": language,
            "vocab_count": len(lp["vocab_known"]),
            "lessons_completed": list(lp["lessons_completed"]),
            "daily_streak": lp["daily_streak"],
            "last_conversation": (self.history["conversations"][-1] if self.history["conversations"] else None),
        }






# -------------------------------------------------
# 2. Proactive Assistance
# -------------------------------------------------

class ProactiveAssistance:
    """
    Anticipates user needs based on patterns and 
    provides assistance proactively.
    """
    
    def __init__(self, memory: ContextualMemory, check_interval: int = 3600):
        """Initialize proactive assistance with contextual memory."""
        self.history = memory
        self.check_interval = check_interval  # seconds
        self.reminders = []
        self.patterns = []
        self._running = False
        self._thread = None
    
    
    def start(self):
        """Start the proactive assistance background thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._background_check, daemon=True)
            self._thread.start()
            logger.info("Proactive assistance started")
    
    def stop(self):
        """Stop the proactive assistance background thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
            logger.info("Proactive assistance stopped")
    
    def _background_check(self):
        """Background thread to check for proactive suggestions."""
        while self._running:
            try:
                self._check_reminders()
                self._check_patterns()
            except Exception as e:
                logger.error(f"Error in proactive assistance: {e}")
            
            # Sleep for the check interval
            for _ in range(self.check_interval):
                if not self._running:
                    break
                threading.Event().wait(1)
    
    def _check_reminders(self):
        """Check for due reminders."""
        now = datetime.datetime.now()
        due_reminders = []
        
        for reminder in self.reminders:
            if now >= reminder["due_time"]:
                due_reminders.append(reminder)
        
        for reminder in due_reminders:
            self.reminders.remove(reminder)
            self._trigger_notification(f"Reminder: {reminder['message']}")
    
    def _check_patterns(self):
        """Check for patterns in user behavior."""
        # This would be more sophisticated in a real implementation
        recent_convs = self.memory.get_recent_conversations(10)
        # Example pattern: User asks about weather at similar times
        # Implementation would depend on specific patterns you want to detect
    
    def add_reminder(self, message: str, due_time: datetime.datetime):
        """Add a reminder to be triggered at the specified time."""
        self.reminders.append({
            "message": message,
            "due_time": due_time,
            "created_at": datetime.datetime.now()
        })
        logger.info(f"Reminder added for {due_time}: {message}")
    
    def add_pattern(self, pattern_type: str, criteria: Dict, action: Dict):
        """Add a pattern to watch for."""
        self.patterns.append({
            "type": pattern_type,
            "criteria": criteria,
            "action": action
        })
    
    def _trigger_notification(self, message: str):
        """Trigger a notification to the user."""
        # In a real implementation, this would send to UI or other notification system
        logger.info(f"NOTIFICATION: {message}")
    
    def suggest(self, user_input: str) -> Optional[str]:
        """
        Suggest a proactive tip based on the user's current input.
        """
        input_lower = user_input.lower()

        if "japan" in input_lower:
            return "Did you know Japan has over 6,800 islands?"
        elif "weather" in input_lower:
            return "Want me to check the current weather for you?"
        elif "python" in input_lower:
            return "Would you like help with some Python code?"
        elif "reminder" in input_lower:
            return "I can set reminders for you if you'd like."
        elif "help" in input_lower:
            return "Need help with something specific? Just ask."

        return None

# Example: could emit an event to be handled by the UI layer


# -------------------------------------------------
# 3. Task Automation
# -------------------------------------------------

class TaskAutomation:
    """
    Handles automation of repetitive tasks based on
    user instructions and patterns.
    """
    
    def __init__(self):
        """Initialize task automation system."""
        self.tasks = {}  # Dictionary of registered tasks

    def handle(self, command: str) -> Optional[str]:
        """
        Process automation-related commands.
        """
        if "timer" in command.lower():
            return "Sure, starting a timer for you!"
        elif "open" in command.lower() and "file" in command.lower():
            return "Okay, which file would you like me to open?"
        else:
            return None  # No action taken
        
    def register_task(self, name: str, handler: Callable, description: str = ""):
        """Register a task handler function."""
        self.tasks[name] = {
            "handler": handler,
            "description": description
        }
        logger.info(f"Registered task: {name}")
    
    def execute_task(self, name: str, **kwargs) -> Dict:
        """Execute a registered task with the given parameters."""
        if name not in self.tasks:
            logger.error(f"Task not found: {name}")
            return {"success": False, "error": "Task not found"}
        
        try:
            result = self.tasks[name]["handler"](**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error executing task {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_tasks(self) -> List[Dict]:
        """Get list of available tasks with descriptions."""
        return [{"name": name, "description": details["description"]} 
                for name, details in self.tasks.items()]
    
    # Example task handlers (would be registered by specific modules)
    @staticmethod
    def _example_email_filter(criteria: Dict) -> Dict:
        """Example task for email filtering."""
        # This would connect to email API in real implementation
        return {"filtered_count": 5}
    
    @staticmethod
    def _example_file_organizer(directory: str, rules: Dict) -> Dict:
        """Example task for file organization."""
        # This would actually organize files in real implementation
        return {"organized_count": 10}

# -------------------------------------------------
# 4. Personalized Knowledge Base
# -------------------------------------------------

# -------------------------------------------------
# 4. Personalized Knowledge Base  (UPDATED)
# -------------------------------------------------

class PersonalizedKnowledgeBase:
    """
    Manages a customized database of information relevant 
    to the user's interests, work, and daily life.
    """

    DEFAULT_CATEGORIES = [
        "documents",
        "interests",
        "work",
        "personal",
        # ✅ New categories:
        "quantum_physics",
        "deep_sea",
    ]
    
    def __init__(self, knowledge_dir: str = "knowledge"):
        """Initialize the personalized knowledge base."""
        self.knowledge_dir = knowledge_dir
        self.indices = {}
        self._ensure_knowledge_structure()

    # ---------- structure / housekeeping ----------
    def _ensure_knowledge_structure(self):
        """Ensure knowledge directory and default category index files exist."""
        os.makedirs(self.knowledge_dir, exist_ok=True)

        # Ensure all default categories have an index
        for category in self.DEFAULT_CATEGORIES:
            self._ensure_category_index(category)

    def _ensure_category_index(self, category: str):
        """Create an index file for a category if missing."""
        index_path = os.path.join(self.knowledge_dir, f"{category}_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding="utf-8") as f:
                    self.indices[category] = json.load(f)
            except Exception:
                # Corrupt or unreadable index → recreate
                self.indices[category] = {"items": []}
                self._save_index(category)
        else:
            self.indices[category] = {"items": []}
            self._save_index(category)

    def _save_index(self, category: str):
        """Save an index to disk."""
        index_path = os.path.join(self.knowledge_dir, f"{category}_index.json")
        with open(index_path, 'w', encoding="utf-8") as f:
            json.dump(self.indices[category], f, indent=2, ensure_ascii=False)

    # ---------- CRUD ----------
    def add_knowledge_item(
        self,
        category: str,
        title: str,
        content: str,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> str:
        """Add an item to the knowledge base and persist content to file."""
        if category not in self.indices:
            # If caller passes a new category, create its index on-the-fly
            self._ensure_category_index(category)

        item_id = f"{category}_{len(self.indices[category]['items'])}"
        now_iso = datetime.datetime.now().isoformat()
        meta = {
            "id": item_id,
            "title": title,
            "source": source,
            "tags": (tags or []),
            "created_at": created_at or now_iso,
            "updated_at": updated_at or now_iso,
        }

        # Write content to separate file (UTF-8)
        content_path = os.path.join(self.knowledge_dir, f"{item_id}.txt")
        with open(content_path, 'w', encoding="utf-8") as f:
            f.write(content)

        # Update index
        self.indices[category]["items"].append(meta)
        self._save_index(category)

        logger.info(f"[KB] Added item '{title}' to '{category}' → {item_id}")
        return item_id

    def update_knowledge_item(
        self,
        item_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Update item metadata and/or content."""
        if "_" not in item_id:
            logger.error(f"[KB] Invalid item_id: {item_id}")
            return False

        category = item_id.split("_", 1)[0]
        if category not in self.indices:
            logger.error(f"[KB] Category not found: {category}")
            return False

        for item in self.indices[category]["items"]:
            if item["id"] == item_id:
                if title is not None:
                    item["title"] = title
                if tags is not None:
                    item["tags"] = tags
                item["updated_at"] = datetime.datetime.now().isoformat()

                if content is not None:
                    content_path = os.path.join(self.knowledge_dir, f"{item_id}.txt")
                    with open(content_path, 'w', encoding="utf-8") as f:
                        f.write(content)

                self._save_index(category)
                logger.info(f"[KB] Updated item {item_id}")
                return True

        logger.error(f"[KB] Item not found: {item_id}")
        return False

    def get_knowledge_item(self, item_id: str) -> Optional[Dict]:
        """Retrieve a full item (metadata + content)."""
        if "_" not in item_id:
            logger.error(f"[KB] Invalid item_id: {item_id}")
            return None

        category = item_id.split("_", 1)[0]
        if category not in self.indices:
            return None

        meta = next((i for i in self.indices[category]["items"] if i["id"] == item_id), None)
        if not meta:
            return None

        content_path = os.path.join(self.knowledge_dir, f"{item_id}.txt")
        try:
            with open(content_path, 'r', encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        out = dict(meta)
        out["content"] = content
        return out

    def search_knowledge(self, query: str, categories: Optional[List[str]] = None) -> List[Dict]:
        """Naive search over titles/tags and file contents (UTF-8)."""
        cats = categories or list(self.indices.keys())
        q = (query or "").strip().lower()
        if not q:
            return []

        results: List[Dict] = []
        for cat in cats:
            if cat not in self.indices:
                continue

            for item in self.indices[cat]["items"]:
                # Title or tags match
                title_match = q in (item.get("title", "").lower())
                tags_match = any(q in (t or "").lower() for t in item.get("tags", []))
                matched = title_match or tags_match

                content_path = os.path.join(self.knowledge_dir, f"{item['id']}.txt")
                content_preview = ""
                if not matched:
                    try:
                        with open(content_path, 'r', encoding="utf-8") as f:
                            content = f.read()
                        pos = content.lower().find(q)
                        if pos >= 0:
                            matched = True
                            start = max(0, pos - 60)
                            end = min(len(content), pos + len(q) + 60)
                            content_preview = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
                    except FileNotFoundError:
                        pass

                if matched:
                    results.append({
                        **item,
                        "category": cat,
                        "preview": content_preview,
                    })

        return results

    # ---------- NEW: bulk import helpers ----------
    def add_bulk_notes(self, category: str, notes: List[Dict[str, Any]]) -> List[str]:
        """
        Bulk-import in-memory notes.
        Each note dict should have: {title: str, content: str, tags?: List[str], source?: str}
        Returns list of item_ids.
        """
        ids: List[str] = []
        for note in notes:
            item_id = self.add_knowledge_item(
                category=category,
                title=note.get("title", "Untitled"),
                content=note.get("content", ""),
                source=note.get("source"),
                tags=note.get("tags") or [],
            )
            ids.append(item_id)
        return ids

    def bulk_import_from_folder(
        self,
        folder_path: str,
        category: str,
        *,
        allowed_exts: Tuple[str, ...] = (".txt", ".md"),
        tag_from_folder: bool = True,
    ) -> List[str]:
        """
        Bulk-import text/markdown files from a folder into a category.
        - allowed_exts controls which files are picked up.
        - If tag_from_folder=True, adds a tag with the folder name.
        Returns list of item_ids created.
        """
        if not os.path.isdir(folder_path):
            logger.error(f"[KB] Folder not found: {folder_path}")
            return []

        tag = os.path.basename(os.path.normpath(folder_path)) if tag_from_folder else None
        created: List[str] = []

        for name in sorted(os.listdir(folder_path)):
            if not name.lower().endswith(allowed_exts):
                continue
            file_path = os.path.join(folder_path, name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                title = os.path.splitext(name)[0]
                tags = [tag] if tag else []
                item_id = self.add_knowledge_item(
                    category=category,
                    title=title,
                    content=content,
                    tags=tags,
                    source=file_path,
                )
                created.append(item_id)
            except Exception as e:
                logger.error(f"[KB] Failed to import '{file_path}': {e}")

        logger.info(f"[KB] Imported {len(created)} notes into '{category}' from '{folder_path}'")
        return created


# -------------------------------------------------
# 5. Smart Device Integration
# -------------------------------------------------

class SmartDeviceIntegration:
    """
    Manages integration with smart home devices and other
    connected systems.
    """
    
    def __init__(self):
        """Initialize smart device integration."""
        self.devices = {}
        self.device_types = set()
        self.platforms = {}
        
    def register_platform(self, platform_id: str, auth_data: Dict,
                         connector_class: Callable):
        """Register a smart home platform (e.g., Hue, Nest, etc.)."""
        try:
            connector = connector_class(**auth_data)
            self.platforms[platform_id] = {
                "connector": connector,
                "auth_data": auth_data
            }
            logger.info(f"Registered platform: {platform_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register platform {platform_id}: {e}")
            return False
    
    def discover_devices(self) -> Dict[str, List[str]]:
        """Discover available devices from all registered platforms."""
        discovered = {}
        
        for platform_id, platform_data in self.platforms.items():
            try:
                devices = platform_data["connector"].discover_devices()
                for device in devices:
                    device_id = f"{platform_id}:{device['id']}"
                    self.devices[device_id] = {
                        "platform": platform_id,
                        "info": device,
                        "type": device.get("type", "unknown")
                    }
                    self.device_types.add(device.get("type", "unknown"))
                
                discovered[platform_id] = [d["info"]["name"] for d in self.devices.values() 
                                          if d["platform"] == platform_id]
            except Exception as e:
                logger.error(f"Error discovering devices for {platform_id}: {e}")
                discovered[platform_id] = []
                
        return discovered
    
    def get_device_status(self, device_id: str) -> Dict:
        """Get current status of a device."""
        if device_id not in self.devices:
            logger.error(f"Device not found: {device_id}")
            return {"error": "Device not found"}
            
        device = self.devices[device_id]
        platform_id = device["platform"]
        
        try:
            status = self.platforms[platform_id]["connector"].get_device_status(
                device["info"]["id"])
            return status
        except Exception as e:
            logger.error(f"Error getting status for device {device_id}: {e}")
            return {"error": str(e)}
    
    def control_device(self, device_id: str, command: str, params: Dict = None) -> Dict:
        """Send control command to a device."""
        if device_id not in self.devices:
            logger.error(f"Device not found: {device_id}")
            return {"success": False, "error": "Device not found"}
            
        device = self.devices[device_id]
        platform_id = device["platform"]
        
        try:
            result = self.platforms[platform_id]["connector"].control_device(
                device["info"]["id"], command, params or {})
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error controlling device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_devices_by_type(self, device_type: str) -> List[Dict]:
        """Get all devices of a specific type."""
        return [
            {"id": device_id, "name": device["info"].get("name", device_id),
             "platform": device["platform"]}
            for device_id, device in self.devices.items()
            if device["type"] == device_type
        ]
    
    def get_device_types(self) -> List[str]:
        """Get list of all available device types."""
        return list(self.device_types)
    
    # Example connector class for smart home platforms
    class ExampleConnector:
        """Example connector for a smart home platform."""
        
        def __init__(self, api_key: str, hub_ip: str = None):
            self.api_key = api_key
            self.hub_ip = hub_ip
            # In real implementation, would connect to actual API
            
        def discover_devices(self) -> List[Dict]:
            """Discover available devices."""
            # In real implementation, would call platform API
            return [
                {"id": "light1", "name": "Living Room Light", "type": "light"},
                {"id": "thermostat1", "name": "Main Thermostat", "type": "thermostat"}
            ]
            
        def get_device_status(self, device_id: str) -> Dict:
            """Get device status."""
            # In real implementation, would call platform API
            if "light" in device_id:
                return {"power": "on", "brightness": 80}
            elif "thermostat" in device_id:
                return {"current_temp": 22.5, "target_temp": 23.0, "mode": "heat"}
            return {}
            
        def control_device(self, device_id: str, command: str, params: Dict) -> Dict:
            """Control a device."""
            # In real implementation, would call platform API
            return {"status": "success"}

# -------------------------------------------------
# 6. Emotional Intelligence
# -------------------------------------------------

class EmotionalIntelligence:
    """
    Provides emotion recognition and appropriate response adaptation
    based on user's emotional state.
    """
    def __init__(self):
        self.emotion_history = []

    def analyze_emotion(self, text: str) -> Dict[str, float]:
        emotions = {
            "joy": 0.0,
            "sadness": 0.0,
            "anger": 0.0,
            "fear": 0.0,
            "surprise": 0.0,
            "neutral": 0.5
        }

        joy_words = ["happy", "great", "excellent", "wonderful", "love", "glad"]
        sad_words = ["sad", "disappointed", "unhappy", "depressed", "miss", "lost"]
        anger_words = ["angry", "annoyed", "frustrated", "mad", "hate", "unfair"]
        fear_words = ["afraid", "scared", "worried", "nervous", "anxious", "terrified"]
        surprise_words = ["wow", "unexpected", "surprised", "shocking", "amazing"]

        text_lower = text.lower()

        for word in joy_words:
            if word in text_lower:
                emotions["joy"] += 0.2
                emotions["neutral"] -= 0.1
        for word in sad_words:
            if word in text_lower:
                emotions["sadness"] += 0.2
                emotions["neutral"] -= 0.1
        for word in anger_words:
            if word in text_lower:
                emotions["anger"] += 0.2
                emotions["neutral"] -= 0.1
        for word in fear_words:
            if word in text_lower:
                emotions["fear"] += 0.2
                emotions["neutral"] -= 0.1
        for word in surprise_words:
            if word in text_lower:
                emotions["surprise"] += 0.2
                emotions["neutral"] -= 0.1

        for emotion in emotions:
            emotions[emotion] = max(0.0, min(1.0, emotions[emotion]))

        emotions["neutral"] = max(0.1, emotions["neutral"])

        self.emotion_history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "emotions": emotions,
            "text": text
        })

        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]

        return emotions

    def get_dominant_emotion(self, emotions: Dict[str, float]) -> str:
        return max(emotions.items(), key=lambda x: x[1])[0]

    def adapt_response(self, original_response: str, user_emotions: Dict[str, float]) -> str:
        dominant = self.get_dominant_emotion(user_emotions)

        if dominant == "neutral" or user_emotions[dominant] < 0.3:
            return original_response

        if dominant == "joy":
            return self._add_warmth(original_response)
        elif dominant == "sadness":
            return self._add_empathy(original_response)
        elif dominant == "anger":
            return self._add_acknowledgment(original_response)
        elif dominant == "fear":
            return self._add_reassurance(original_response)
        elif dominant == "surprise":
            return self._add_acknowledgment(original_response)

        return original_response

    def analyze_and_respond(self, text: str) -> Optional[str]:
        emotions = self.analyze_emotion(text)
        dominant_emotion = self.get_dominant_emotion(emotions)

        if dominant_emotion == "neutral" or emotions[dominant_emotion] < 0.4:
            return None

        if dominant_emotion == "sadness":
            return "I'm here for you. It's okay to feel this way."
        elif dominant_emotion == "anger":
            return "I can tell something’s frustrating you. Want to talk about it?"
        elif dominant_emotion == "fear":
            return "You’re not alone. I’m with you."
        elif dominant_emotion == "joy":
            return "That’s awesome to hear!"
        elif dominant_emotion == "surprise":
            return "Whoa! That *does* sound surprising."

        return None

    
    def _add_warmth(self, text: str) -> str:
        """Add warm tone to response."""
        warmth_prefixes = [
            "I'm glad to hear that! ",
            "That's wonderful! ",
            "Great to hear! "
        ]
        
        if any(text.startswith(prefix) for prefix in warmth_prefixes):
            return text
            
        return f"{warmth_prefixes[0]}{text}"
    
    def _add_empathy(self, text: str) -> str:
        """Add empathy to response."""
        empathy_prefixes = [
            "I understand this is difficult. ",
            "I'm sorry to hear that. ",
            "That sounds challenging. "
        ]
        
        if any(text.startswith(prefix) for prefix in empathy_prefixes):
            return text
            
        return f"{empathy_prefixes[0]}{text}"
    
    def _add_acknowledgment(self, text: str) -> str:
        """Add acknowledgment to response."""
        ack_prefixes = [
            "I understand your frustration. ",
            "I can see why that would be concerning. ",
            "That's a valid reaction. "
        ]
        
        if any(text.startswith(prefix) for prefix in ack_prefixes):
            return text
            
        return f"{ack_prefixes[0]}{text}"
    
    def _add_reassurance(self, text: str) -> str:
        """Add reassurance to response."""
        reassurance_prefixes = [
            "Don't worry, ",
            "It's going to be okay. ",
            "Let me help you with this. "
        ]
        
        if any(text.startswith(prefix) for prefix in reassurance_prefixes):
            return text
            
        return f"{reassurance_prefixes[0]}{text}"
    
    def get_emotional_trend(self, time_period: int = 24) -> Dict:
        """
        Analyze emotional trend over a time period (in hours).
        Returns dominant emotions and their average intensities.
        """
        if not self.emotion_history:
            return {"dominant": "neutral", "average": {"neutral": 1.0}}
            
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=time_period)
        cutoff_str = cutoff_time.isoformat()
        
        # Filter history by time
        recent_emotions = [entry for entry in self.emotion_history 
                          if entry["timestamp"] > cutoff_str]
        
        if not recent_emotions:
            return {"dominant": "neutral", "average": {"neutral": 1.0}}
            
        # Calculate averages
        emotion_sums = {}
        for entry in recent_emotions:
            for emotion, value in entry["emotions"].items():
                if emotion in emotion_sums:
                    emotion_sums[emotion] += value
                else:
                    emotion_sums[emotion] = value
        
        # Get averages
        emotion_avgs = {emotion: value / len(recent_emotions) 
                       for emotion, value in emotion_sums.items()}
        
        # Get dominant emotion
        dominant = max(emotion_avgs.items(), key=lambda x: x[1])[0]
        
        return {
            "dominant": dominant,
            "average": emotion_avgs
        }

# -------------------------------------------------
# 7. Privacy Controls
# -------------------------------------------------

class PrivacyControls:
    """
    Manages user privacy settings and data retention policies.
    """
    
    def __init__(self, settings_file: str = "privacy/settings.json"):
        """Initialize privacy controls with default settings."""
        self.settings_file = settings_file
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        self.settings = self._load_settings()
        self._ensure_default_settings()
        
    def _load_settings(self) -> Dict:
        """Load privacy settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading privacy settings: {e}")
            return {}
    
    def _ensure_default_settings(self):
        """Ensure all default privacy settings exist."""
        defaults = {
            "data_retention": {
                "conversation_history_days": 30,
                "keep_user_preferences": True,
                "keep_learned_entities": True
            },
            "data_sharing": {
                "allow_anonymized_data": False, 
                "allow_third_party_processing": False
            },
            "sensitive_topics": {
                "health": False,
                "financial": False,
                "location": False,
                "personal_relationships": False
            },
            "service_integration": {
                "allow_cloud_processing": True,
                "allow_api_calls": True
            }
        }
        
        # Apply defaults for any missing settings
        for category, options in defaults.items():
            if category not in self.settings:
                self.settings[category] = {}
            
            for option, value in options.items():
                if option not in self.settings[category]:
                    self.settings[category][option] = value
        
        # Save settings
        self._save_settings()
    
    def _save_settings(self):
        """Save privacy settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving privacy settings: {e}")
    
    def update_setting(self, category: str, setting: str, value: Any) -> bool:
        """Update a specific privacy setting."""
        if category not in self.settings:
            logger.error(f"Privacy category not found: {category}")
            return False
            
        if setting not in self.settings[category]:
            logger.error(f"Privacy setting not found: {setting} in {category}")
            return False
            
        # Update the setting
        self.settings[category][setting] = value
        self._save_settings()
        logger.info(f"Updated privacy setting {category}.{setting} to {value}")
        return True
    
    def get_setting(self, category: str, setting: str) -> Any:
        """Get a specific privacy setting."""
        try:
            return self.settings[category][setting]
        except KeyError:
            logger.error(f"Privacy setting not found: {category}.{setting}")
            return None
    
    def get_category_settings(self, category: str) -> Dict:
        """Get all settings in a category."""
        return self.settings.get(category, {})
    
    def get_all_settings(self) -> Dict:
        """Get all privacy settings."""
        return self.settings
    
    def should_retain_data(self, data_type: str) -> bool:
        """Check if specific type of data should be retained."""
        if data_type == "conversation":
            # Check if conversations should be kept at all
            days = self.settings["data_retention"]["conversation_history_days"]
            return days > 0
        elif data_type == "preferences":
            return self.settings["data_retention"]["keep_user_preferences"]
        elif data_type == "entities":
            return self.settings["data_retention"]["keep_learned_entities"]
        else:
            # Default to false for unknown data types
            logger.warning(f"Unknown data type for retention check: {data_type}")
            return False
    
    def clean_expired_data(self, memory: "ContextualMemory"):
        """Clean expired data according to retention settings."""
    # Use memory.history (not memory.memory)
        hist = memory.history

    # Check conversation retention
        days = self.settings["data_retention"]["conversation_history_days"]
        if days <= 0:
            hist["conversations"] = []
        else:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            hist["conversations"] = [
            conv for conv in hist.get("conversations", [])
            if conv.get("timestamp", "") > cutoff_str ]

    # Check preference retention
        if not self.settings["data_retention"]["keep_user_preferences"]:
            hist["preferences"] = {}

    # Check entity retention
        if not self.settings["data_retention"]["keep_learned_entities"]:
            hist["entities"] = {}

    # Save back to disk
        memory.save()
    logger.info("Cleaned expired data according to privacy settings")

# -------------------------------------------------
# 8. Voice Interface Integration 
# -------------------------------------------------

class VoiceInterface:
    """
    Manages voice input/output capabilities for the assistant.
    """
    
    def __init__(self, voice_config: Dict = None):
        """Initialize voice interface with configuration."""
        self.config = voice_config or {
            "voice_id": "default",
            "speed": 1.0,
            "pitch": 1.0
        }
        self.is_listening = False
        self._speech_recognition_active = False
        
    def start_listening(self):
        """Start listening for voice input."""
        if self.is_listening:
            logger.info("Already listening for voice input")
            return False
            
        try:
            # In a real implementation, would initialize microphone
            self.is_listening = True
            self._speech_recognition_active = True
            logger.info("Started listening for voice input")
            return True
        except Exception as e:
            logger.error(f"Error starting voice input: {e}")
            return False
    
    def stop_listening(self):
        """Stop listening for voice input."""
        if not self.is_listening:
            return False
            
        try:
            # In a real implementation, would close microphone
            self.is_listening = False
            self._speech_recognition_active = False
            logger.info("Stopped listening for voice input")
            return True
        except Exception as e:
            logger.error(f"Error stopping voice input: {e}")
            return False
    
    def recognize_speech(self, audio_data=None) -> Dict:
        """
        Process audio data and convert to text.
        If audio_data is None, records from microphone.
        """
        # In a real implementation, would use an ASR service or library
        # Here we simulate a successful recognition
        if not audio_data and not self.is_listening:
            return {"success": False, "error": "Not listening"}
            
        try:
            # Simulated recognition result
            recognized_text = "This is a simulated voice recognition result"
            return {
                "success": True, 
                "text": recognized_text, 
                "confidence": 0.95
            }
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            return {"success": False, "error": str(e)}
    
    def text_to_speech(self, text: str) -> Dict:
        """Convert text to speech audio."""
        # In a real implementation, would use a TTS service or library
        try:
            # Simulate TTS processing
            logger.info(f"Converting to speech: {text[:20]}...")
            return {
                "success": True,
                "message": "Text successfully converted to speech"
            }
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return {"success": False, "error": str(e)}
    
    def update_voice_config(self, config_updates: Dict) -> bool:
        """Update voice configuration parameters."""
        try:
            self.config.update(config_updates)
            logger.info(f"Updated voice config: {config_updates}")
            return True
        except Exception as e:
            logger.error(f"Error updating voice config: {e}")
            return False
    
    def get_voice_config(self) -> Dict:
        """Get current voice configuration."""
        return self.config

# -------------------------------------------------
# 9. Multi-modal Processing
# -------------------------------------------------

class MultiModalProcessor:
    """
    Handles processing of different types of input/output
    including text, images, and other media.
    """
    
    def __init__(self):
        """Initialize multi-modal processor."""
        self.supported_input_types = ["text", "image"]
        self.supported_output_types = ["text", "image"]
        
    def process_input(self, input_data: Any, input_type: str) -> Dict:
        """Process input of specified type."""
        if input_type not in self.supported_input_types:
            logger.error(f"Unsupported input type: {input_type}")
            return {"success": False, "error": f"Unsupported input type: {input_type}"}
            
        try:
            if input_type == "text":
                return self._process_text_input(input_data)
            elif input_type == "image":
                return self._process_image_input(input_data)
            else:
                return {"success": False, "error": "Unhandled input type"}
        except Exception as e:
            logger.error(f"Error processing {input_type} input: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_output(self, data: Dict, output_type: str) -> Dict:
        """Generate output of specified type."""
        if output_type not in self.supported_output_types:
            logger.error(f"Unsupported output type: {output_type}")
            return {"success": False, "error": f"Unsupported output type: {output_type}"}
            
        try:
            if output_type == "text":
                return self._generate_text_output(data)
            elif output_type == "image":
                return self._generate_image_output(data)
            else:
                return {"success": False, "error": "Unhandled output type"}
        except Exception as e:
            logger.error(f"Error generating {output_type} output: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_text_input(self, text: str) -> Dict:
        """Process text input."""
        # In a real implementation, would do NLP processing
        return {
            "success": True,
            "processed_data": {
                "text": text,
                "tokens": len(text.split()),
                "sentiment": "neutral"  # Simplified
            }
        }
    
    def _process_image_input(self, image_data: bytes) -> Dict:
        """Process image input."""
        # In a real implementation, would do image analysis
        return {
            "success": True,
            "processed_data": {
                "size": len(image_data),
                "detected_objects": ["example_object"],  # Simplified
                "description": "A sample image description"  # Simplified
            }
        }
    
    def _generate_text_output(self, data: Dict) -> Dict:
        """Generate text output."""
        # In a real implementation, would generate text based on input data
        if "response" not in data:
            return {"success": False, "error": "No response data provided"}
            
        return {
            "success": True,
            "output": data["response"]
        }
    
    def _generate_image_output(self, data: Dict) -> Dict:
        """Generate image output."""
        # In a real implementation, would generate or modify images
        if "image_prompt" not in data:
            return {"success": False, "error": "No image prompt provided"}
            
        # Simulated image generation
        return {
            "success": True,
            "message": f"Generated image from prompt: {data['image_prompt'][:30]}..."
        }
    
    def extract_entities_from_image(self, image_data: bytes) -> Dict:
        """Extract entities and information from an image."""
        # In a real implementation, would use computer vision
        return {
            "entities": [
                {"type": "person", "confidence": 0.95},
                {"type": "object", "label": "example", "confidence": 0.85}
            ],
            "text": "Sample text extracted from image",
            "scene_description": "A sample scene description"
        }
    
    def convert_image_to_text(self, image_data: bytes) -> str:
        """Extract text content from image (OCR)."""
        # In a real implementation, would use OCR
        return "Sample text extracted from image using OCR"

# -------------------------------------------------
# 10. Main Integration Class
# -------------------------------------------------

class REYA_AI:
    """
    Main class that integrates all advanced features 
    for the AI assistant.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize REYA AI with all components."""
        self.config = self._load_config(config_path)
        
        # Initialize all components
        self.memory = ContextualMemory()
        self.proactive = ProactiveAssistance(self.memory)
        self.automation = TaskAutomation()
        self.knowledge = PersonalizedKnowledgeBase()
        self.devices = SmartDeviceIntegration()
        self.emotions = EmotionalIntelligence()
        self.privacy = PrivacyControls()
        self.voice = VoiceInterface()
        self.multimodal = MultiModalProcessor()
        
        # Register builtin tasks
        self._register_builtin_tasks()
        
        logger.info("REYA-AI initialized with all components")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration file."""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "assistant_name": "REYA",
                    "user_name": "User",
                    "voice_enabled": False,
                    "proactive_enabled": True,
                    "features_enabled": {
                        "contextual_memory": True,
                        "proactive_assistance": True,
                        "task_automation": True,
                        "knowledge_base": True,
                        "smart_devices": False,
                        "emotional_intelligence": True,
                        "privacy_controls": True,
                        "voice_interface": False,
                        "multimodal": True
                    }
                }
                
                # Save default config
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                    
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _register_builtin_tasks(self):
        """Register built-in automation tasks."""
        # Example tasks - in a real implementation would have actual functionality
        self.automation.register_task(
            "summarize_text", 
            lambda text: {"summary": "Example summary of text"},
            "Summarize long text into key points"
        )
        
        self.automation.register_task(
            "organize_calendar", 
            lambda days=7: {"organized_events": 5},
            "Organize and optimize calendar events"
        )
        
        self.automation.register_task(
            "filter_emails", 
            lambda criteria: {"filtered": 3},
            "Filter and categorize emails based on criteria"
        )
    
    def process_input(self, user_input: str, input_type: str = "text") -> Dict:
        """
        Process user input and generate an appropriate response
        using available advanced features. This method does NOT
        call the LLM directly (your FastAPI /chat route does that);
        it focuses on orchestration, memory, emotions, and helpers.
        """
        out: Dict[str, Any] = {"success": True, "input_type": input_type}

        try:
            if input_type == "voice":
                # 1) ASR -> text
                asr = self.voice.recognize_speech()
                if not asr.get("success"):
                    return {"success": False, "error": asr.get("error", "ASR failed")}
                transcript = asr.get("text", "").strip()
                out["transcript"] = transcript

                # 2) Reuse text flow
                return self.process_input(transcript, input_type="text")

            elif input_type == "image":
                # Placeholder: you can extend with real CV/OCR later
                out["text_response"] = "Image processing not fully implemented yet"
                # Memory write (log that an image interaction occurred)
                self.memory.remember(
                    user_input="[image]",
                    assistant_response=out["text_response"]
                )
                return out

            elif input_type == "text":
                # --- Emotion analysis & tone adaptation ---
                emotions = self.emotions.analyze_emotion(user_input)
                dominant = self.emotions.get_dominant_emotion(emotions)
                out["detected_emotions"] = emotions
                out["dominant_emotion"] = dominant

                # You can replace this canned reply with your LLM’s reply
                base_reply = f"Processed: {user_input}"

                # Optional proactive suggestion (lightweight heuristic)
                suggestion = self.proactive.suggest(user_input)
                if suggestion:
                    out["proactive_suggestion"] = suggestion

                # Adapt tone
                adapted = self.emotions.adapt_response(base_reply, emotions)
                out["text_response"] = adapted

                # --- Persist to contextual memory (✅ correct method) ---
                self.memory.remember(user_input, adapted)

                return out

            else:
                return {"success": False, "error": f"Unsupported input type: {input_type}"}

        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    
    def start(self):
        """Start all background services."""
        if self.config["proactive_enabled"]:
            self.proactive.start()
        logger.info("REYA-AI services started")
    
    def stop(self):
        """Stop all background services."""
        self.proactive.stop()
        logger.info("REYA-AI services stopped")
        
    def register_platform(self, platform_id: str, auth_data: Dict) -> bool:
        """Register a smart home platform."""
        # Example platform registration
        connector_class = SmartDeviceIntegration.ExampleConnector
        return self.devices.register_platform(platform_id, auth_data, connector_class)

# -------------------------------------------------
# Usage Example
# -------------------------------------------------

def main():
    """Example usage of REYA-AI."""
    # Initialize REYA
    reya = REYA_AI()
    
    # Start services
    reya.start()
    
    try:
        # Example interaction
        print("REYA-AI initialized and ready!")
        
        # Process some example inputs
        responses = [
            reya.process_input("Hello, what can you help me with today?"),
            reya.process_input("I'm feeling a bit stressed about my workload"),
            reya.process_input("Can you remind me to call Mom tomorrow at 5pm?")
        ]
        
        # Add some example knowledge
        reya.knowledge.add_knowledge_item(
            "personal", 
            "Work Project Notes", 
            "Important deadline on Friday for the quarterly report.",
            tags=["work", "deadline", "report"]
        )
        
        # Example privacy settings
        reya.privacy.update_setting("data_retention", "conversation_history_days", 14)
        
        # Example smart home interaction (would need actual platform registration)
        # reya.register_platform("hue", {"api_key": "example_key"})
        # reya.devices.discover_devices()
        
    finally:
        # Stop services
        reya.stop()

if __name__ == "__main__":
    main()