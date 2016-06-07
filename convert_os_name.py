import uuid
from oslo_serialization import base64

# name = "f22b7386-775d-4c69-81e6-ec89c6b0cfe9"
name = "e64d5ada-ad35-413e-a4f0-d106712617f8"
uuid_str = name.replace("-", "")
vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
vol_encoded = base64.encode_as_text(vol_uuid.bytes)

# 3par doesn't allow +, nor /
vol_encoded = vol_encoded.replace('+', '.')
vol_encoded = vol_encoded.replace('/', '-')
# strip off the == as 3par doesn't like those.
vol_encoded = vol_encoded.replace('=', '')
print vol_encoded
