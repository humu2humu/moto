package dev.moto.spots

/** スポットの取得元。実データ(API・DB)に差し替えるときはこれを実装する。 */
fun interface SpotRepository {
    fun all(): List<Spot>
}

class SpotFinder(private val repository: SpotRepository) {

    /**
     * [origin] から近い順に [category] のスポットを返す。
     *
     * @param limit 返す最大件数。PlaceListMapTemplate はホストごとに表示上限があるため小さめにする。
     * @param maxDistanceMeters これより遠いスポットは除外する(null なら制限なし)。
     */
    fun nearby(
        origin: GeoPoint,
        category: SpotCategory,
        limit: Int = DEFAULT_LIMIT,
        maxDistanceMeters: Double? = null,
    ): List<NearbySpot> {
        require(limit >= 0) { "limit must be >= 0: $limit" }
        require(maxDistanceMeters == null || maxDistanceMeters >= 0.0) {
            "maxDistanceMeters must be >= 0: $maxDistanceMeters"
        }
        return repository.all()
            .asSequence()
            .filter { it.category == category }
            .map { NearbySpot(it, distanceMeters(origin, it.location)) }
            .filter { maxDistanceMeters == null || it.distanceMeters <= maxDistanceMeters }
            .sortedWith(compareBy<NearbySpot> { it.distanceMeters }.thenBy { it.spot.id })
            .take(limit)
            .toList()
    }

    companion object {
        const val DEFAULT_LIMIT = 6
    }
}
