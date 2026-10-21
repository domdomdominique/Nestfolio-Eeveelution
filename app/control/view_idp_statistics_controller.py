from app.control.view_portfolio_controller import ViewPortfolioController


class ViewIDPStatisticsController:
    def view(self, account_id):
        return ViewPortfolioController().view(account_id)