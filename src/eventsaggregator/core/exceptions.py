class EventNotFound(Exception):
    pass


class EventNotPublished(Exception):
    pass


class RegistrationDeadlinePassed(Exception):
    pass


class InvalidSeat(Exception):
    pass


class InvalidBody(Exception):
    pass


class ProviderError(Exception):
    pass


class TicketNotFound(Exception):
    pass


class TicketRegisterError(Exception):
    pass


class TicketUnequalPayload(Exception):
    pass
