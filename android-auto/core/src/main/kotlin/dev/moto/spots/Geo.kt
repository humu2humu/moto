package dev.moto.spots

import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

private const val EARTH_RADIUS_METERS = 6_371_000.0

/** 2 点間の大円距離(ハバーサイン公式, メートル)。 */
fun distanceMeters(a: GeoPoint, b: GeoPoint): Double {
    val lat1 = Math.toRadians(a.latitude)
    val lat2 = Math.toRadians(b.latitude)
    val dLat = lat2 - lat1
    val dLon = Math.toRadians(b.longitude - a.longitude)
    val h = sin(dLat / 2).pow(2) + cos(lat1) * cos(lat2) * sin(dLon / 2).pow(2)
    // 浮動小数の誤差で h がわずかに 1 を超えると asin が NaN になるため丸める。
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(min(1.0, h)))
}

enum class DistanceUnit { METERS, KILOMETERS, KILOMETERS_ONE_DECIMAL }

/** 車載画面向けの表示用距離。Car App Library の Distance.create に渡す値と単位。 */
data class DisplayDistance(val value: Double, val unit: DistanceUnit)

/**
 * メートルを運転中に読みやすい形にする。
 * - 1 km 未満: 10 m 単位(例: 340 m)
 * - 10 km 未満: 小数 1 桁の km(例: 2.4 km)
 * - それ以上: 整数の km(例: 15 km)
 */
fun toDisplayDistance(meters: Double): DisplayDistance {
    require(meters >= 0.0 && meters.isFinite()) { "meters must be finite and >= 0: $meters" }
    val roundedMeters = Math.round(meters / 10.0) * 10.0
    return when {
        roundedMeters < 1_000.0 -> DisplayDistance(roundedMeters, DistanceUnit.METERS)
        meters < 9_950.0 -> DisplayDistance(Math.round(meters / 100.0) / 10.0, DistanceUnit.KILOMETERS_ONE_DECIMAL)
        else -> DisplayDistance(Math.round(meters / 1_000.0).toDouble(), DistanceUnit.KILOMETERS)
    }
}

/** 表示用距離の文字列(例: "340 m", "2.4 km", "15 km")。 */
fun formatDistance(meters: Double): String {
    val d = toDisplayDistance(meters)
    return when (d.unit) {
        DistanceUnit.METERS -> "${d.value.toLong()} m"
        DistanceUnit.KILOMETERS_ONE_DECIMAL -> "${"%.1f".format(java.util.Locale.ROOT, d.value)} km"
        DistanceUnit.KILOMETERS -> "${d.value.toLong()} km"
    }
}
