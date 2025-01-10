import dill
import codecs

class SerializationError(Exception):
    """Custom exception for serialization errors."""
    def __init__(self, message):
        super().__init__(message)

class DeserializationError(Exception):
    """Custom exception for deserialization errors."""
    def __init__(self, message):
        super().__init__(message)

def serialize(obj) -> str:
    """Serialize a Python object to a base64-encoded string."""
    try :
        return codecs.encode(dill.dumps(obj), "base64").decode()
    except Exception as e:
        raise SerializationError(f"Failed to serialize object: {e}") from e

def deserialize(obj: str):
    """Deserialize a Python object from a base64-encoded string."""
    try :
        return dill.loads(codecs.decode(obj.encode(), "base64"))
    except Exception as e:
        raise DeserializationError(f"Failed to deserialize object: {e}") from e
