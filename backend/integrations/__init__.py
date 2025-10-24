from .base import ALMIntegration
from .jira import JiraIntegration
from .azure_devops import AzureDevOpsIntegration
from .polarion import PolarionIntegration
# from .polarion import PolarionIntegration

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
        return AzureDevOpsIntegration()
    elif integration_name == "polarion":
        return PolarionIntegration()
    # elif integration_name == "azure_devops":
    #     return AzureDevOpsIntegration()
    # elif integration_name == "polarion":
    #     return PolarionIntegration()
    else:
        raise ValueError(f"Unknown integration: {integration_name}")
