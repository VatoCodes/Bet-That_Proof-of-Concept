"""Edge Calculator Modules

This package contains specialized edge detection calculators for various betting strategies.

Available Calculators:
    - FirstHalfTotalCalculator: First Half Total Under edges
    - QBTDCalculatorV2: Enhanced QB TD 0.5+ prop edges
    - KickerPointsCalculator: Kicker Points Over edges (coming soon)
"""

from .first_half_total_calculator import FirstHalfTotalCalculator
from .qb_td_calculator_v2 import QBTDCalculatorV2

__all__ = [
    'FirstHalfTotalCalculator',
    'QBTDCalculatorV2',
]
