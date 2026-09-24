class PlatformException(Exception):
    """Base exception for all healthcare platform errors."""
    pass

class ClinicalSafetyViolation(PlatformException):
    """Raised when an action violates non-negotiable patient safety gates."""
    pass

class UnanchoredChargeError(ClinicalSafetyViolation):
    """Raised when an attempt is made to post a financial charge without a clinical order origin."""
    pass

class ImbalancedLedgerError(PlatformException):
    """Raised when a double-entry journal entry does not balance debits and credits."""
    pass

class IdentityResolutionError(PlatformException):
    """Raised when patient identity resolution encounters an unrecoverable conflict."""
    pass

class DuplicateIdentityCandidateException(IdentityResolutionError):
    """Raised when a high-confidence duplicate is identified requiring front-desk or HIM review."""
    def __init__(self, message: str, candidate_matches: list):
        super().__init__(message)
        self.candidate_matches = candidate_matches
