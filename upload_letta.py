from upload_function_to_openwebui_ import upload_function

# Read the letta.py file
with open('letta_improved.py', 'r') as f:
    letta_content = f.read()

# Upload the function
result = upload_function(
    name="Letta",
    content=letta_content,
    description="Interactive Letta AI integration with event emitters and configurable settings"
)

if result:
    print("Letta function uploaded successfully!")
    print("Function ID:", result.get("id"))
else:
    print("Failed to upload Letta function")