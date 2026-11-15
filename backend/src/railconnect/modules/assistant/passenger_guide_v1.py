from railconnect.modules.assistant.retrieval import PolicyChunk

SOURCE_ID = "railconnect-passenger-guide"
SOURCE_VERSION = "1"

PASSENGER_GUIDE_V1 = (
    PolicyChunk(
        source_id=SOURCE_ID,
        source_version=SOURCE_VERSION,
        chunk_id="search-direct-journeys",
        title="Search for a direct journey",
        text=(
            "In Journey search, select a departure station, an arrival station and a travel "
            "date. The travel date is the boarding date in Sri Lanka time. Use Arrive by to "
            "set an optional arrival deadline. For an overnight journey, set the arrival "
            "deadline date as well."
        ),
    ),
    PolicyChunk(
        source_id=SOURCE_ID,
        source_version=SOURCE_VERSION,
        chunk_id="report-disruption",
        title="Report a disruption",
        text=(
            "Open Report a disruption and enter a title, a description and the observation "
            "time in Sri Lanka time. After submission, the receipt shows that the report is "
            "pending staff review. A pending report does not change journey results."
        ),
    ),
    PolicyChunk(
        source_id=SOURCE_ID,
        source_version=SOURCE_VERSION,
        chunk_id="interpret-delay-estimates",
        title="Understand a verified delay and estimated arrival",
        text=(
            "Journey results and details show scheduled times alongside estimates when a "
            "verified delay applies. Use Refresh journey details or Refresh journey results "
            "to see the latest information held by RailConnect."
        ),
    ),
    PolicyChunk(
        source_id=SOURCE_ID,
        source_version=SOURCE_VERSION,
        chunk_id="check-direct-alternatives",
        title="Check direct alternatives",
        text=(
            "Open journey details and choose Check direct alternatives. RailConnect checks "
            "prepared direct services for the same stations and boarding date. It excludes "
            "the original run and applies the selected arrival deadline. If no prepared "
            "direct service meets those criteria, it displays an empty-state message."
        ),
    ),
    PolicyChunk(
        source_id=SOURCE_ID,
        source_version=SOURCE_VERSION,
        chunk_id="demonstration-coverage",
        title="Understand demonstration timetable coverage",
        text=(
            "RailConnect uses fictional demonstration schedules covering selected Sri Lankan "
            "stations. Journey search uses prepared runs for specific dates. An empty result "
            "can mean the date or route is outside the prepared demo coverage."
        ),
    ),
)
