from app.control.view_portfolio_controller import ViewPortfolioController


# ID-13 view counts and ID-14 shortlist counts for each of the designer's IDPs.
class ViewIDPStatisticsController:
    def view(self, account_id):
        return ViewPortfolioController().all_projects(account_id)