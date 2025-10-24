from abc import ABC, abstractmethod
from typing import Dict, Any

class ALMIntegration(ABC):
    """
    Abstract base class for Application Lifecycle Management (ALM) integrations.
    """

    @abstractmethod
    def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an issue in the ALM tool.

        Args:
            issue_data: A dictionary containing the issue data.

        Returns:
            A dictionary containing the created issue's information.
        """
        pass
