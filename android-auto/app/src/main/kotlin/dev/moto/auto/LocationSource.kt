package dev.moto.auto

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import dev.moto.spots.GeoPoint
import dev.moto.spots.SampleSpots

/** 検索の起点。現在地が取れないときは既定地点を使い、そのことを画面に出す。 */
data class Origin(val point: GeoPoint, val isCurrentLocation: Boolean)

object LocationSource {

    private val PERMISSIONS = listOf(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION,
    )

    val requestablePermissions: List<String> get() = PERMISSIONS

    fun hasPermission(context: Context): Boolean =
        PERMISSIONS.any { context.checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }

    /** 最後に取得された位置(最新のもの)を返す。権限がない・位置がない場合は既定地点。 */
    fun currentOrigin(context: Context): Origin {
        if (!hasPermission(context)) return Origin(SampleSpots.DEFAULT_ORIGIN, isCurrentLocation = false)
        val manager = context.getSystemService(LocationManager::class.java)
            ?: return Origin(SampleSpots.DEFAULT_ORIGIN, isCurrentLocation = false)
        val latest: Location? = try {
            manager.getProviders(true)
                .mapNotNull { manager.getLastKnownLocation(it) }
                .maxByOrNull { it.time }
        } catch (e: SecurityException) {
            // 権限確認後に取り消された場合など。
            null
        }
        return if (latest != null) {
            Origin(GeoPoint(latest.latitude, latest.longitude), isCurrentLocation = true)
        } else {
            Origin(SampleSpots.DEFAULT_ORIGIN, isCurrentLocation = false)
        }
    }
}
