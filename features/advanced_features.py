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
    """
    Maintains persistent memory of user interactions and preferences
    to provide personalized responses over time.
    """
    
    def __init__(self, memory_file: str = "memory/user_context.json"):
        """Initialize the contextual memory system."""
        self.memory_file = memory_file
        self.memory = self._load_memory()
        self._ensure_memory_structure()
    def _ensure_memory_structure(self):
        """Ensure all required memory structures exist."""
        if "conversations" not in self.memory:
            self.memory["conversations"] = []
        if "preferences" not in self.memory:
            self.memory["preferences"] = {}
        if "entities" not in self.memory:
            self.memory["entities"] = {}
        if "frequent_topics" not in self.memory:
            self.memory["frequent_topics"] = {}
            
    def _load_memory(self) -> Dict:
        """Load memory from file or create if it doesn't exist."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            return {}
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return {}
    
    def save(self):
        """Save memory to file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def add_conversation(self, user_input: str, assistant_response: str, 
                         context: Dict = None, timestamp: str = None):
        """Add a conversation exchange to memory."""
        if timestamp is None:
            timestamp = datetime.datetime.now().isoformat()
        
        conversation = {
            "user_input": user_input,
            "assistant_response": assistant_response,
            "timestamp": timestamp,
            "context": context or {}
        }
        
        self.memory["conversations"].append(conversation)
        self._update_frequent_topics(user_input)
        self.save()
        
    def _update_frequent_topics(self, text: str):
        """Update the frequency count of topics based on keywords."""
        # Simple keyword extraction (in a real system, use NLP)
        keywords = re.findall(r'\b\w{4,}\b', text.lower())
        for keyword in keywords:
            if keyword in self.memory["frequent_topics"]:
                self.memory["frequent_topics"][keyword] += 1
            else:
                self.memory["frequent_topics"][keyword] = 1
    
    def set_preference(self, category: str, key: str, value: Any):
        """Set a user preference."""
        if category not in self.memory["preferences"]:
            self.memory["preferences"][category] = {}
            
        self.memory["preferences"][category][key] = value
        self.save()
    
    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        try:
            return self.memory["preferences"][category][key]
        except KeyError:
            return default
    
    def add_entity(self, entity_type: str, name: str, properties: Dict):
        """Add or update an entity (person, place, thing)."""
        if entity_type not in self.memory["entities"]:
            self.memory["entities"][entity_type] = {}
            
        if name in self.memory["entities"][entity_type]:
            self.memory["entities"][entity_type][name].update(properties)
        else:
            self.memory["entities"][entity_type][name] = properties
            
        self.save()
    
    def get_entity(self, entity_type: str, name: str) -> Optional[Dict]:
        """Get information about a specific entity."""
        try:
            return self.memory["entities"][entity_type][name]
        except KeyError:
            return None
    
    def get_recent_conversations(self, count: int = 5) -> List[Dict]:
        """Retrieve the most recent conversations."""
        return self.memory["conversations"][-count:] if self.memory["conversations"] else []
    
    def search_conversations(self, query: str) -> List[Dict]:
        """Search conversations for a specific query."""
        results = []
        for conv in self.memory["conversations"]:
            if (query.lower() in conv["user_input"].lower() or 
                query.lower() in conv["assistant_response"].lower()):
                results.append(conv)
        return results
    
    def get_most_frequent_topics(self, count: int = 5) -> List[Tuple[str, int]]:
        """Get the most frequently discussed topics."""
        topics = sorted(self.memory["frequent_topics"].items(), 
                       key=lambda x: x[1], reverse=True)
        return topics[:count]
    
    def recall(self) -> str:
     """Return the last 5 interactions as a formatted string."""
     history = self.get_recent_conversations()
     return "\n".join(
        [f"User: {conv['user_input']}\nREYA: {conv['assistant_response']}" for conv in history]
    ) or "No prior context."


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
        self.memory = memory
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

class PersonalizedKnowledgeBase:
    """
    Manages a customized database of information relevant 
    to the user's interests, work, and daily life.
    """
    
    def __init__(self, knowledge_dir: str = "knowledge"):
        """Initialize the personalized knowledge base."""
        self.knowledge_dir = knowledge_dir
        self.indices = {}
        self._ensure_knowledge_structure()
        
    def _ensure_knowledge_structure(self):
        """Ensure knowledge directory and files exist."""
        os.makedirs(self.knowledge_dir, exist_ok=True)
        
        # Create indices for different knowledge categories
        categories = ["documents", "interests", "work", "personal"]
        for category in categories:
            index_path = os.path.join(self.knowledge_dir, f"{category}_index.json")
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    self.indices[category] = json.load(f)
            else:
                self.indices[category] = {"items": []}
                self._save_index(category)
    
    def _save_index(self, category: str):
        """Save an index to disk."""
        index_path = os.path.join(self.knowledge_dir, f"{category}_index.json")
        with open(index_path, 'w') as f:
            json.dump(self.indices[category], f, indent=2)
    
    def add_knowledge_item(self, category: str, title: str, content: str, 
                         source: str = None, tags: List[str] = None):
        """Add an item to the knowledge base."""
        if category not in self.indices:
            self.indices[category] = {"items": []}
            
        item_id = f"{category}_{len(self.indices[category]['items'])}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Create knowledge item
        item = {
            "id": item_id,
            "title": title,
            "source": source,
            "tags": tags or [],
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        # Save the content to a separate file
        content_path = os.path.join(self.knowledge_dir, f"{item_id}.txt")
        with open(content_path, 'w') as f:
            f.write(content)
            
        # Add to index
        self.indices[category]["items"].append(item)
        self._save_index(category)
        
        logger.info(f"Added knowledge item: {title} in {category}")
        return item_id
    
    def update_knowledge_item(self, item_id: str, title: str = None, 
                            content: str = None, tags: List[str] = None):
        """Update an existing knowledge item."""
        # Extract category from item_id
        if "_" not in item_id:
            logger.error(f"Invalid item_id format: {item_id}")
            return False
            
        category = item_id.split("_")[0]
        if category not in self.indices:
            logger.error(f"Category not found: {category}")
            return False
            
        # Find the item
        for item in self.indices[category]["items"]:
            if item["id"] == item_id:
                if title:
                    item["title"] = title
                if tags:
                    item["tags"] = tags
                item["updated_at"] = datetime.datetime.now().isoformat()
                
                # Update content if provided
                if content:
                    content_path = os.path.join(self.knowledge_dir, f"{item_id}.txt")
                    with open(content_path, 'w') as f:
                        f.write(content)
                
                self._save_index(category)
                logger.info(f"Updated knowledge item: {item_id}")
                return True
                
        logger.error(f"Item not found: {item_id}")
        return False
    
    def get_knowledge_item(self, item_id: str) -> Dict:
        """Retrieve a knowledge item by ID."""
        if "_" not in item_id:
            logger.error(f"Invalid item_id format: {item_id}")
            return None
            
        category = item_id.split("_")[0]
        if category not in self.indices:
            logger.error(f"Category not found: {category}")
            return None
        
        # Find item metadata in index
        item_metadata = None
        for item in self.indices[category]["items"]:
            if item["id"] == item_id:
                item_metadata = item
                break
                
        if not item_metadata:
            logger.error(f"Item not found: {item_id}")
            return None
            
        # Get content
        content_path = os.path.join(self.knowledge_dir, f"{item_id}.txt")
        try:
            with open(content_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            logger.error(f"Content file not found for {item_id}")
            content = ""
            
        # Return combined item
        result = item_metadata.copy()
        result["content"] = content
        return result
    
    def search_knowledge(self, query: str, categories: List[str] = None) -> List[Dict]:
        """Search knowledge base for items matching the query."""
        if not categories:
            categories = list(self.indices.keys())
            
        results = []
        for category in categories:
            if category not in self.indices:
                continue
                
            for item in self.indices[category]["items"]:
                # Check in metadata
                if (query.lower() in item["title"].lower() or
                    any(query.lower() in tag.lower() for tag in item["tags"])):
                    
                    # Get a preview of content
                    content_path = os.path.join(self.knowledge_dir, f"{item['id']}.txt")
                    try:
                        with open(content_path, 'r') as f:
                            content = f.read(200)  # Get first 200 chars for preview
                    except FileNotFoundError:
                        content = ""
                    
                    result = item.copy()
                    result["preview"] = content
                    results.append(result)
                    continue
                
                # Check in full content
                content_path = os.path.join(self.knowledge_dir, f"{item['id']}.txt")
                try:
                    with open(content_path, 'r') as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            result = item.copy()
                            # Find the matching context
                            idx = content.lower().find(query.lower())
                            start = max(0, idx - 50)
                            end = min(len(content), idx + len(query) + 50)
                            preview = "..." if start > 0 else ""
                            preview += content[start:end]
                            preview += "..." if end < len(content) else ""
                            result["preview"] = preview
                            results.append(result)
                except FileNotFoundError:
                    pass
                    
        return results

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
        """Initialize emotional intelligence system."""
        self.emotion_history = []
        
    def analyze_emotion(self, text: str) -> Dict[str, float]:
        """
        Analyze text for emotional content.
        Returns dict of emotion -> confidence scores.
        """
        # In a real implementation, this would use NLP/ML
        # Here we use a simplified rule-based approach
        emotions = {
            "joy": 0.0,
            "sadness": 0.0,
            "anger": 0.0,
            "fear": 0.0,
            "surprise": 0.0,
            "neutral": 0.5  # Default to somewhat neutral
        }
        
        # Simple keyword matching (very simplified)
        joy_words = ["happy", "great", "excellent", "wonderful", "love", "glad"]
        sad_words = ["sad", "disappointed", "unhappy", "depressed", "miss", "lost"]
        anger_words = ["angry", "annoyed", "frustrated", "mad", "hate", "unfair"]
        fear_words = ["afraid", "scared", "worried", "nervous", "anxious", "terrified"]
        surprise_words = ["wow", "unexpected", "surprised", "shocking", "amazing"]
        
        text_lower = text.lower()
        
        # Check for each emotion type
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
        
        # Normalize values between 0 and 1
        for emotion in emotions:
            emotions[emotion] = max(0.0, min(1.0, emotions[emotion]))
            
        # Ensure neutral is at least slightly positive
        emotions["neutral"] = max(0.1, emotions["neutral"])
        
        # Record emotion in history
        self.emotion_history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "emotions": emotions,
            "text": text
        })
        
        # Keep history to a reasonable size
        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]
            
        return emotions
    
    def get_dominant_emotion(self, emotions: Dict[str, float]) -> str:
        """Get the dominant emotion from an emotion analysis."""
        return max(emotions.items(), key=lambda x: x[1])[0]
    
    def adapt_response(self, original_response: str, 
                      user_emotions: Dict[str, float]) -> str:
        """
        Adapt response based on detected user emotions.
        """
        dominant = self.get_dominant_emotion(user_emotions)
        
        # No adaptation needed for neutral emotions
        if dominant == "neutral" or user_emotions[dominant] < 0.3:
            return original_response
            
        # Based on dominant emotion, adapt the response
        if dominant == "joy":
            # Match positive energy
            return self._add_warmth(original_response)
            
        elif dominant == "sadness":
            # Be more supportive and empathetic
            return self._add_empathy(original_response)
            
        elif dominant == "anger":
            # Be calming and acknowledge frustration
            return self._add_acknowledgment(original_response)
            
        elif dominant == "fear":
            # Be reassuring
            return self._add_reassurance(original_response)
            
        elif dominant == "surprise":
            # Match excitement or provide stability based on context
            return self._add_acknowledgment(original_response)
            
        return original_response
    
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
    
    def clean_expired_data(self, memory: ContextualMemory):
        """Clean expired data according to retention settings."""
        # Check conversation retention setting
        days = self.settings["data_retention"]["conversation_history_days"]
        if days <= 0:
            # Delete all conversations
            memory.memory["conversations"] = []
        else:
            # Delete conversations older than retention period
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            memory.memory["conversations"] = [
                conv for conv in memory.memory["conversations"]
                if conv["timestamp"] > cutoff_str
            ]
        
        # Check preference retention
        if not self.settings["data_retention"]["keep_user_preferences"]:
            memory.memory["preferences"] = {}
            
        # Check entity retention
        if not self.settings["data_retention"]["keep_learned_entities"]:
            memory.memory["entities"] = {}
            
        # Save cleaned memory
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
        Process user input and generate appropriate response
        with all the advanced features.
        """
        response = {"success": True}
        
        try:
            # Process input based on type
            if input_type == "text":
                # Basic text response
                response["text_response"] = f"Processed: {user_input}"
                
                # Analyze emotions
                emotions = self.emotions.analyze_emotion(user_input)
                response["detected_emotions"] = emotions
                
                # Add to memory
                self.memory.add_conversation(user_input, response["text_response"])
                
                # Check for tasks that could be automated
                # In real implementation, would have NLP to detect task requests
                
                # Adapt response based on emotions
                response["text_response"] = self.emotions.adapt_response(
                    response["text_response"], emotions)
                
            elif input_type == "voice":
                # Process voice through voice interface
                speech_result = self.voice.recognize_speech()
                if speech_result["success"]:
                    # Process the recognized text
                    text_response = self.process_input(speech_result["text"], "text")
                    response.update(text_response)
                else:
                    response["success"] = False
                    response["error"] = speech_result["error"]
                    
            elif input_type == "image":
                # In real implementation, would receive image data
                response["text_response"] = "Image processing not fully implemented yet"
                
            else:
                response["success"] = False
                response["error"] = f"Unsupported input type: {input_type}"
                
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            response["success"] = False
            response["error"] = str(e)
            
        return response
    
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