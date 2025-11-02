from .base import ALMIntegration
from .jira import JiraIntegration
from .polarion import PolarionIntegration

# Import Azure DevOps conditionally to prevent startup failures
try:
    from .azure_devops import AzureDevOpsIntegration
    AZURE_DEVOPS_AVAILABLE = True
except ImportError as e:
    print(f"Azure DevOps integration not available: {e}")
    AZURE_DEVOPS_AVAILABLE = False
    AzureDevOpsIntegration = None

def get_integration(integration_name: str) -> ALMIntegration:
    """
    Factory function to get an instance of an ALM integration.

    Args:
        integration_name: The name of the integration to get.

    Returns:
        An instance of the specified ALM integration.
    """
    if integration_name == "jira":
        return JiraIntegration()
    elif integration_name == "azure_devops":
        if not AZURE_DEVOPS_AVAILABLE:
            raise ValueError("Azure DevOps integration is not available due to missing dependencies or configuration")
        return AzureDevOpsIntegration()
    elif integration_name == "polarion":
        return PolarionIntegration()
    else:
        raise ValueError(f"Unknown integration: {integration_name}")
