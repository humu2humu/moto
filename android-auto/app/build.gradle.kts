plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "dev.moto.auto"
    compileSdk = 35

    defaultConfig {
        applicationId = "dev.moto.auto"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // includeBuild("core") が group:name で置き換える。
    implementation("dev.moto:core")
    implementation("androidx.car.app:app:1.4.0")
}
