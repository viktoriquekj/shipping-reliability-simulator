from dataclasses import dataclass, field


@dataclass
class Segment:
    """
    One segment of a shipping route — either a port call or a transit leg.

    Attributes
    ----------
    name                 : human-readable label (e.g. 'Rotterdam port delay')
    scheduled_days       : planned duration in days
    delay_distribution   : frozen scipy distribution to sample delays from
    is_port              : True = port call segment, False = transit leg
    congestion_port      : port name for congestion lookup (None for transit)
    """
    name:               str
    scheduled_days:     float
    delay_distribution: object          # frozen scipy distribution
    is_port:            bool  = False
    congestion_port:    str   = None    # 'Rotterdam', 'Singapore', 'Shanghai'


@dataclass
class Route:
    """
    A full shipping route composed of ordered segments.

    Attributes
    ----------
    name     : route label (e.g. 'Rotterdam → Singapore → Shanghai')
    segments : ordered list of Segment objects
    """
    name:     str
    segments: list = field(default_factory=list)

    @property
    def scheduled_total(self) -> float:
        """Sum of all segment scheduled durations."""
        return sum(s.scheduled_days for s in self.segments)

    @property
    def port_segments(self) -> list:
        """Return only port call segments."""
        return [s for s in self.segments if s.is_port]

    @property
    def transit_segments(self) -> list:
        """Return only transit leg segments."""
        return [s for s in self.segments if not s.is_port]

    def __repr__(self) -> str:
        return (
            f"Route('{self.name}', "
            f"{len(self.segments)} segments, "
            f"scheduled={self.scheduled_total:.1f}d)"
        )