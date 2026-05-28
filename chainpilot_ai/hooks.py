app_name = "chainpilot_ai"
app_title = "ChainPilot AI"
app_publisher = "ChainPilot AI Team"
app_description = "SAP-connected supply chain AI decision and execution agent"
app_email = "maintainers@example.com"
app_license = "MIT"

fixtures = [
    {"doctype": "Role", "filters": [["role_name", "like", "ChainPilot%"]]},
    {"doctype": "Workspace", "filters": [["name", "=", "ChainPilot AI"]]},
]

app_include_js = ["/assets/chainpilot_ai/js/chainpilot_ai.js"]
