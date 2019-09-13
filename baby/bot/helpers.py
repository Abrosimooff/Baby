from dateutil.relativedelta import relativedelta


class DateUtil:

    @staticmethod
    def delta(max_date, min_date):
        return relativedelta(max_date, min_date)

    def delta_string(self, max_date, min_date):
        delta=self.delta(max_date, min_date)
        data_list = []
        if delta.years:
            data_list.append('{} {}'.format(delta.years, self.year_str(delta.years)))
        if delta.months:
            data_list.append('{} {}'.format(delta.months, self.month_str(delta.months)))
        if delta.weeks:
            data_list.append('{} {}'.format(delta.weeks, self.week_str(delta.weeks)))
        return ', '.join(data_list)

    @staticmethod
    def year_str(year):
        if year == 1:
            return 'год'
        elif year < 5:
            return 'года'
        return 'лет'

    @staticmethod
    def month_str(month):
        if month == 1:
            return 'месяц'
        elif month < 5:
            return 'месяца'
        return 'месяцев'

    @staticmethod
    def week_str(week):
        return 'неделя' if week == 1 else 'недели'

