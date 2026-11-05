package dev.moto.auto

import androidx.car.app.CarContext
import androidx.car.app.Screen
import androidx.car.app.model.Action
import androidx.car.app.model.ActionStrip
import androidx.car.app.model.CarColor
import androidx.car.app.model.ItemList
import androidx.car.app.model.Metadata
import androidx.car.app.model.ParkedOnlyOnClickListener
import androidx.car.app.model.Place
import androidx.car.app.model.PlaceListMapTemplate
import androidx.car.app.model.PlaceMarker
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import dev.moto.spots.SampleSpots
import dev.moto.spots.SpotCategory
import dev.moto.spots.SpotFinder

/** 選んだ種類のスポットを、近い順に地図つきリストで表示する。 */
class SpotListScreen(
    carContext: CarContext,
    private val category: SpotCategory,
) : Screen(carContext) {

    private val finder = SpotFinder(SampleSpots)

    override fun onGetTemplate(): Template {
        val origin = LocationSource.currentOrigin(carContext)
        val nearby = finder.nearby(origin.point, category, maxDistanceMeters = MAX_DISTANCE_METERS)

        val items = ItemList.Builder()
            .setNoItemsMessage("${MAX_DISTANCE_METERS.toInt() / 1000} km 以内に${category.label}が見つかりません")
        nearby.forEachIndexed { index, item ->
            val marker = PlaceMarker.Builder().setLabel((index + 1).toString()).build()
            items.addItem(
                Row.Builder()
                    .setTitle(item.spot.name)
                    .addText(distanceText(item.distanceMeters, item.spot.note))
                    .setMetadata(
                        Metadata.Builder()
                            .setPlace(Place.Builder(item.spot.location.toCarLocation()).setMarker(marker).build())
                            .build(),
                    )
                    .setOnClickListener { screenManager.push(SpotDetailScreen(carContext, item)) }
                    .build(),
            )
        }

        val title = if (origin.isCurrentLocation) category.label else "${category.label}(東京駅周辺)"
        val template = PlaceListMapTemplate.Builder()
            .setTitle(title)
            .setHeaderAction(Action.BACK)
            .setItemList(items.build())
            .setAnchor(
                Place.Builder(origin.point.toCarLocation())
                    .setMarker(PlaceMarker.Builder().setColor(CarColor.BLUE).build())
                    .build(),
            )

        if (!LocationSource.hasPermission(carContext)) {
            template.setActionStrip(
                ActionStrip.Builder()
                    .addAction(
                        Action.Builder()
                            .setTitle("現在地を使う")
                            // 権限ダイアログはスマホ側に出るので、停車中のみ操作可能にする。
                            .setOnClickListener(ParkedOnlyOnClickListener.create { requestLocationPermission() })
                            .build(),
                    )
                    .build(),
            )
        }
        return template.build()
    }

    private fun requestLocationPermission() {
        carContext.requestPermissions(LocationSource.requestablePermissions) { _, _ -> invalidate() }
    }

    private companion object {
        const val MAX_DISTANCE_METERS = 20_000.0
    }
}
