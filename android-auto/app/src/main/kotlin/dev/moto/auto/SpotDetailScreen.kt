package dev.moto.auto

import android.content.Intent
import android.net.Uri
import androidx.car.app.CarContext
import androidx.car.app.CarToast
import androidx.car.app.HostException
import androidx.car.app.Screen
import androidx.car.app.model.Action
import androidx.car.app.model.Pane
import androidx.car.app.model.PaneTemplate
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import dev.moto.spots.NearbySpot
import dev.moto.spots.formatDistance

/** スポットの詳細とナビ開始ボタン。 */
class SpotDetailScreen(
    carContext: CarContext,
    private val item: NearbySpot,
) : Screen(carContext) {

    override fun onGetTemplate(): Template {
        val spot = item.spot
        val pane = Pane.Builder()
            .addRow(Row.Builder().setTitle("距離").addText(formatDistance(item.distanceMeters)).build())
            .addRow(Row.Builder().setTitle("住所").addText(spot.address).build())
        if (spot.note.isNotEmpty()) {
            pane.addRow(Row.Builder().setTitle("メモ").addText(spot.note).build())
        }
        pane.addAction(
            Action.Builder()
                .setTitle("ナビ開始")
                .setOnClickListener { startNavigation() }
                .build(),
        )
        return PaneTemplate.Builder(pane.build())
            .setTitle(spot.name)
            .setHeaderAction(Action.BACK)
            .build()
    }

    private fun startNavigation() {
        val loc = item.spot.location
        // Car App Library 仕様: ACTION_NAVIGATE + "geo:lat,lng" で既定のナビアプリに引き渡す。
        val intent = Intent(CarContext.ACTION_NAVIGATE, Uri.parse("geo:${loc.latitude},${loc.longitude}"))
        try {
            carContext.startCarApp(intent)
        } catch (e: HostException) {
            CarToast.makeText(carContext, "ナビアプリを起動できませんでした", CarToast.LENGTH_LONG).show()
        } catch (e: SecurityException) {
            CarToast.makeText(carContext, "ナビアプリを起動できませんでした", CarToast.LENGTH_LONG).show()
        }
    }
}
