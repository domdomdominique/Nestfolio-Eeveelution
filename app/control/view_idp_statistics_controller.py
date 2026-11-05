from app.control.view_portfolio_controller import ViewPortfolioController
from app.entity.activity_timeline import ActivityTimeline


# ID-13 view counts and ID-14 shortlist counts for each of the designer's IDPs.
class ViewIDPStatisticsController:
    def view(self, account_id):
        return ViewPortfolioController().all_projects(account_id)

    def activity(self, account_id, days=30):
        """Views and shortlists of this designer's own IDPs per day, for the chart."""
        ViewPortfolioController().all_projects(account_id)  # same checks: an active designer
        return ActivityTimeline.last_days(days, designer_id=account_id)