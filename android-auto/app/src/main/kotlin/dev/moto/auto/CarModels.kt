package dev.moto.auto

import android.text.SpannableString
import android.text.Spanned
import androidx.car.app.model.CarLocation
import androidx.car.app.model.Distance
import androidx.car.app.model.DistanceSpan
import dev.moto.spots.DistanceUnit
import dev.moto.spots.GeoPoint
import dev.moto.spots.toDisplayDistance

/** core の表示用距離を Car App Library の Distance に変換する。 */
fun carDistance(meters: Double): Distance {
    val display = toDisplayDistance(meters)
    val unit = when (display.unit) {
        DistanceUnit.METERS -> Distance.UNIT_METERS
        DistanceUnit.KILOMETERS -> Distance.UNIT_KILOMETERS
        DistanceUnit.KILOMETERS_ONE_DECIMAL -> Distance.UNIT_KILOMETERS_P1
    }
    return Distance.create(display.value, unit)
}

/**
 * 先頭に DistanceSpan を付けた行テキスト。PlaceListMapTemplate は各行に DistanceSpan を要求する。
 * 先頭の 1 文字(プレースホルダ)がホストによって距離表示に置き換えられる。
 */
fun distanceText(meters: Double, suffix: String): CharSequence {
    val text = if (suffix.isEmpty()) " " else "  ·  $suffix"
    return SpannableString(text).apply {
        setSpan(DistanceSpan.create(carDistance(meters)), 0, 1, Spanned.SPAN_INCLUSIVE_INCLUSIVE)
    }
}

fun GeoPoint.toCarLocation(): CarLocation = CarLocation.create(latitude, longitude)
