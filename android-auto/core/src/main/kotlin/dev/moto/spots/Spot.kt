package dev.moto.spots

/** Android Auto の画面に出すスポットの種類。 */
enum class SpotCategory(val label: String) {
    FUEL("ガソリンスタンド"),
    MOTO_PARKING("バイク駐車場"),
    REST("休憩スポット"),
}

data class GeoPoint(val latitude: Double, val longitude: Double) {
    init {
        require(latitude in -90.0..90.0) { "latitude out of range: $latitude" }
        require(longitude in -180.0..180.0) { "longitude out of range: $longitude" }
    }
}

data class Spot(
    val id: String,
    val name: String,
    val category: SpotCategory,
    val location: GeoPoint,
    val address: String,
    val note: String = "",
)

/** 検索地点からの距離つきのスポット。 */
data class NearbySpot(val spot: Spot, val distanceMeters: Double)
