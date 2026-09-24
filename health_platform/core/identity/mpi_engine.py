import math
from datetime import date
from typing import Tuple, List, Optional
from health_platform.core.identity.models import PatientRegistrationRequest, PatientRecord

def jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    """Computes Jaro-Winkler string similarity metric."""
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_dist = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions //= 2
    jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0

    # Common prefix up to 4 characters
    l = 0
    for i in range(min(4, min(len1, len2))):
        if s1[i] == s2[i]:
            l += 1
        else:
            break

    return jaro + l * p * (1.0 - jaro)


def soundex(name: str) -> str:
    """Computes Soundex phonetic encoding as a robust pure-python fallback."""
    name = name.upper()
    if not name:
        return "0000"
    first_letter = name[0]
    mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    encoded = [first_letter]
    prev = mapping.get(first_letter, '0')
    for char in name[1:]:
        code = mapping.get(char, '0')
        if code != '0' and code != prev:
            encoded.append(code)
            prev = code
        elif code == '0':
            prev = '0'
    res = "".join(encoded)[:4]
    return res.ljust(4, '0')


class FellegiSunterMPIEngine:
    """
    Implements Fellegi-Sunter probabilistic identity deduplication matching 
    as formally specified in the Platform Architecture Blueprint.
    """

    # Weights defined in Section 3.2 of the specification:
    W_FIRST_NAME_AGREE = 7.52
    W_FIRST_NAME_DISAGREE = -3.63

    W_LAST_NAME_AGREE = 6.21
    W_LAST_NAME_DISAGREE = -3.01

    W_DOB_EXACT_AGREE = 11.63
    W_DOB_EXACT_DISAGREE = -4.32
    W_DOB_TRANSPOSITION = 9.64

    W_GENDER_AGREE = 0.98
    W_GENDER_DISAGREE = -5.64

    W_POSTAL_AGREE = 5.40
    W_POSTAL_DISAGREE = -2.71

    W_MOBILE_AGREE = 9.60
    W_MOBILE_DISAGREE = -1.62

    # Thresholds
    THRESHOLD_HIGH_CONFIDENCE = 18.5  # Duplicate candidate prompt
    THRESHOLD_LOW_REVIEW = 12.0       # HIM manual review queue

    @classmethod
    def evaluate_pair(
        cls, 
        req: PatientRegistrationRequest, 
        existing: PatientRecord,
        existing_postal_code: Optional[str] = None
    ) -> Tuple[float, List[str]]:
        """
        Computes the composite weight W for a candidate pair and returns 
        the score with contributing rule explanations.
        """
        score = 0.0
        reasons = []

        # 1. First Name Comparison
        jw_first = jaro_winkler(req.first_name, existing.first_name)
        sdx_req_first = soundex(req.first_name)
        sdx_ext_first = soundex(existing.first_name)
        if jw_first >= 0.90 or sdx_req_first == sdx_ext_first:
            score += cls.W_FIRST_NAME_AGREE
            reasons.append(f"First Name Agreement (Jaro: {jw_first:.2f}, Phonetic: {sdx_req_first})")
        else:
            score += cls.W_FIRST_NAME_DISAGREE

        # 2. Last Name Comparison
        jw_last = jaro_winkler(req.last_name, existing.last_name)
        sdx_req_last = soundex(req.last_name)
        sdx_ext_last = soundex(existing.last_name)
        if jw_last >= 0.88 or sdx_req_last == sdx_ext_last:
            score += cls.W_LAST_NAME_AGREE
            reasons.append(f"Last Name Agreement (Jaro: {jw_last:.2f}, Phonetic: {sdx_req_last})")
        else:
            score += cls.W_LAST_NAME_DISAGREE

        # 3. Date of Birth Comparison & Transposition Check
        if req.dob == existing.dob:
            score += cls.W_DOB_EXACT_AGREE
            reasons.append(f"Exact Date of Birth Match ({req.dob})")
        elif (req.dob.year == existing.dob.year and 
              req.dob.month == existing.dob.day and 
              req.dob.day == existing.dob.month):
            # Transposed Day & Month (e.g. 12/04 vs 04/12)
            score += cls.W_DOB_TRANSPOSITION
            reasons.append(f"DOB Day-Month Transposition Detected ({req.dob} vs {existing.dob})")
        else:
            score += cls.W_DOB_EXACT_DISAGREE

        # 4. Gender Comparison
        if req.gender == existing.gender:
            score += cls.W_GENDER_AGREE
            reasons.append(f"Gender Agreement ({req.gender.value})")
        else:
            score += cls.W_GENDER_DISAGREE

        # 5. Postal PIN Code Comparison
        if req.postal_code and existing_postal_code:
            if req.postal_code.strip() == existing_postal_code.strip():
                score += cls.W_POSTAL_AGREE
                reasons.append(f"Postal Code Match ({req.postal_code})")
            else:
                score += cls.W_POSTAL_DISAGREE

        # 6. Mobile Number Match
        if req.primary_phone and existing.primary_phone:
            # Normalize E.164
            p1 = req.primary_phone.replace("+", "").replace(" ", "").replace("-", "")[-10:]
            p2 = existing.primary_phone.replace("+", "").replace(" ", "").replace("-", "")[-10:]
            if p1 == p2:
                score += cls.W_MOBILE_AGREE
                reasons.append("Primary Mobile Match")
            else:
                score += cls.W_MOBILE_DISAGREE

        return round(score, 2), reasons
