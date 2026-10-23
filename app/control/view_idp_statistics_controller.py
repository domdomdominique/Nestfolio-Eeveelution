from app.control.view_portfolio_controller import ViewPortfolioController


class ViewIDPStatisticsController:
    def view(self, account_id):
        return ViewPortfolioController().all_projects(account_id)