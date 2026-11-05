// core は Android SDK に依存しない純 Kotlin ライブラリ。
// 単独でも `gradle -p android-auto/core test` でビルド・テストできるよう独立ビルドにしている。
pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

rootProject.name = "core"
