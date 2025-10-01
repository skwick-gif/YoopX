
// qml/Main.qml — fixed: uses FileDialog (selectFolder) instead of FolderDialog.
// Ready-to-drop file. No manual edits needed.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Dialogs 1.3

ApplicationWindow {
    id: win
    width: 1280
    height: 820
    visible: true
    title: "QuantDesk"
    Material.theme: Material.Light
    Material.accent: Material.Indigo

    property string dataDir: "."

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            Label { text: win.title; font.pixelSize: 18; Layout.alignment: Qt.AlignVCenter }
            Item { Layout.fillWidth: true }
            Switch {
                id: dark; text: dark.checked ? "Dark" : "Light"
                onCheckedChanged: Material.theme = dark.checked ? Material.Dark : Material.Light
            }
        }
    }

    TabBar {
        id: tabs
        width: parent.width
        currentIndex: 2
        TabButton { text: "Scan" }
        TabButton { text: "Backtest" }
        TabButton { text: "Optimize" }
        TabButton { text: "Live (IBKR)" }
        TabButton { text: "Help" }
    }

    StackLayout {
        anchors.fill: parent
        anchors.topMargin: tabs.height + 8
        currentIndex: tabs.currentIndex

        // --- Scan (placeholder) ---
        Item {
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                GroupBox {
                    title: "Setup"
                    Layout.fillWidth: true
                    RowLayout {
                        anchors.margins: 12; spacing: 12
                        TextField { id: dirField1; placeholderText: "נתיב תיקייה ל-JSON/CSV"; text: win.dataDir; Layout.preferredWidth: 420 }
                        Button { text: "Browse"; onClicked: folderDlg.open() }
                        CheckBox { id: useAdj1; text: "Adjusted Close" }
                        TextField { id: startDate1; placeholderText: "YYYY-MM-DD"; Layout.preferredWidth: 140 }
                        Button { text: "Run SCAN"; onClicked: controller.runScan(
                            dirField1.text, useAdj1.checked, startDate1.text,
                            "SMA Cross",
                            10, 20, 200,
                            20, 10,
                            2, 10, 60,
                            20, 2.0,
                            false, false,
                            "Fixed", 1, 0.01, 14, 2.0,
                            1.5, "boll_mid",
                            true, false, 0.1,
                            false, true, 15, 0.5,
                            30, "ENGULFING,DOJI,HAMMER"
                        )}
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 34; color: "#f2f2f2"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 8
                        Label { text: "Symbol"; Layout.preferredWidth: 120; font.bold: true }
                        Label { text: "Pass"; Layout.preferredWidth: 60; font.bold: true }
                        Label { text: "Signal"; Layout.preferredWidth: 80; font.bold: true }
                        Label { text: "Age"; Layout.preferredWidth: 60; font.bold: true }
                        Label { text: "PriceAt"; Layout.preferredWidth: 100; font.bold: true }
                        Label { text: "R:R"; Layout.preferredWidth: 60; font.bold: true }
                        Label { text: "Patterns"; Layout.fillWidth: true; font.bold: true }
                    }
                }
                ListView {
                    id: scanList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    model: scanModel
                    delegate: Rectangle {
                        width: scanList.width; height: 30
                        color: index % 2 === 0 ? "transparent" : "#fbfbfb"
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 8; spacing: 8
                            Label { text: Symbol; Layout.preferredWidth: 120 }
                            Label { text: Pass; Layout.preferredWidth: 60 }
                            Label { text: SignalNOW; Layout.preferredWidth: 80 }
                            Label { text: SignalAge; Layout.preferredWidth: 60 }
                            Label { text: PriceAtSignal; Layout.preferredWidth: 100 }
                            Label { text: RR; Layout.preferredWidth: 60 }
                            Label { text: Patterns; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
                }
            }
        }

        // --- Backtest (placeholder) ---
        Item {
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                GroupBox {
                    title: "Backtest"
                    Layout.fillWidth: true
                    RowLayout {
                        anchors.margins: 12; spacing: 12
                        TextField { id: dirField2; placeholderText: "נתיב תיקייה ל-JSON/CSV"; text: win.dataDir; Layout.preferredWidth: 420 }
                        Button { text: "Browse"; onClicked: folderDlg.open() }
                        CheckBox { id: useAdj2; text: "Adjusted Close" }
                        TextField { id: startDate2; placeholderText: "YYYY-MM-DD"; Layout.preferredWidth: 140 }
                        Button { text: "Run Backtest"; onClicked: controller.runBacktest(
                            dirField2.text, useAdj2.checked, startDate2.text,
                            "SMA Cross",
                            10, 20, 200,
                            20, 10,
                            2, 10, 60,
                            20, 2.0,
                            false, false,
                            "Fixed", 1, 0.01, 14, 2.0
                        )}
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 34; color: "#f2f2f2"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 8
                        Label { text: "Symbol"; Layout.preferredWidth: 120; font.bold: true }
                        Label { text: "Final"; Layout.preferredWidth: 100; font.bold: true }
                        Label { text: "Sharpe"; Layout.preferredWidth: 80; font.bold: true }
                        Label { text: "MaxDD%"; Layout.preferredWidth: 80; font.bold: true }
                        Label { text: "WinRate%"; Layout.preferredWidth: 90; font.bold: true }
                        Label { text: "Trades"; Layout.preferredWidth: 80; font.bold: true }
                        Label { text: "CAGR%"; Layout.preferredWidth: 80; font.bold: true }
                    }
                }
                ListView {
                    id: btList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    model: btModel
                    delegate: Rectangle {
                        width: btList.width; height: 30
                        color: index % 2 === 0 ? "transparent" : "#fbfbfb"
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 8; spacing: 8
                            Label { text: Symbol; Layout.preferredWidth: 120 }
                            Label { text: Final_Value; Layout.preferredWidth: 100 }
                            Label { text: Sharpe; Layout.preferredWidth: 80 }
                            Label { text: MaxDD_pct; Layout.preferredWidth: 80 }
                            Label { text: WinRate_pct; Layout.preferredWidth: 90 }
                            Label { text: Trades; Layout.preferredWidth: 80 }
                            Label { text: CAGR_pct; Layout.preferredWidth: 80 }
                        }
                    }
                }
            }
        }

        // --- Optimize ---
        Item {
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                GroupBox {
                    title: "Setup"
                    Layout.fillWidth: true
                    RowLayout {
                        anchors.margins: 12; spacing: 12
                        TextField { id: dirField; placeholderText: "נתיב תיקייה ל-JSON/CSV"; text: win.dataDir; Layout.preferredWidth: 420 }
                        Button { text: "Browse"; onClicked: folderDlg.open() }
                        ComboBox { id: strat; model: ["SMA Cross","EMA Cross","Donchian Breakout","MACD Trend","RSI(2) @ Bollinger"]; Layout.preferredWidth: 230 }
                        TextField { id: startDate; placeholderText: "YYYY-MM-DD"; Layout.preferredWidth: 140 }
                        CheckBox { id: useAdj; text: "Adjusted Close" }
                    }
                }

                GroupBox {
                    title: "Parameter Ranges (JSON)"
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.margins: 12
                        TextArea {
                            id: ranges; Layout.fillWidth: true; Layout.preferredHeight: 160
                            text: '{\n  "fast": [8, 20, 4],\n  "slow": [20, 60, 10],\n  "ema_trend": [100, 200, 50]\n}'
                            wrapMode: TextEdit.NoWrap
                            selectByMouse: true
                        }
                        RowLayout {
                            spacing: 12
                            SpinBox { id: universe; from:0; to:10000; value:50; editable: true; }
                            Label { text: "Universe" }
                            SpinBox { id: folds; from:1; to:10; value:3; editable: true; }
                            Label { text: "Folds" }
                            SpinBox { id: oos; from:5; to:80; value:20; editable: true; }
                            Label { text: "OOS %" }
                            SpinBox { id: minTrades; from:0; to:1000; value:5; editable: true; }
                            Label { text: "Min Trades" }
                            ComboBox { id: objective; model: ["Sharpe","CAGR","Return/DD","WinRate","Trades"]; Layout.preferredWidth: 150 }
                            Button { text: "Run Optimize"; onClicked: controller.runOptimize(
                                        dirField.text, useAdj.checked, startDate.text,
                                        strat.currentText,
                                        ranges.text,
                                        universe.value,
                                        oos.value/100.0,
                                        folds.value,
                                        minTrades.value,
                                        objective.currentIndex
                                    ) }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 34; color: "#f2f2f2"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 8
                        Label { text: "Rank"; Layout.preferredWidth: 60; font.bold: true }
                        Label { text: "Params"; Layout.fillWidth: true; font.bold: true }
                        Label { text: "Score"; Layout.preferredWidth: 80; font.bold: true }
                        Label { text: "Sharpe"; Layout.preferredWidth: 90; font.bold: true }
                        Label { text: "CAGR%"; Layout.preferredWidth: 90; font.bold: true }
                        Label { text: "MaxDD%"; Layout.preferredWidth: 90; font.bold: true }
                        Label { text: "WinRate%"; Layout.preferredWidth: 90; font.bold: true }
                        Label { text: "Trades"; Layout.preferredWidth: 80; font.bold: true }
                        Label { text: "Univ"; Layout.preferredWidth: 60; font.bold: true }
                        Label { text: "Folds"; Layout.preferredWidth: 60; font.bold: true }
                    }
                }

                ListView {
                    id: optList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    model: optModel
                    delegate: Rectangle {
                        width: optList.width; height: 32
                        color: index % 2 === 0 ? "transparent" : "#fbfbfb"
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 8; spacing: 8
                            Label { text: Rank; Layout.preferredWidth: 60 }
                            Label { text: Params; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: Score; Layout.preferredWidth: 80 }
                            Label { text: Sharpe; Layout.preferredWidth: 90 }
                            Label { text: CAGR_pct; Layout.preferredWidth: 90 }
                            Label { text: MaxDD_pct; Layout.preferredWidth: 90 }
                            Label { text: WinRate_pct; Layout.preferredWidth: 90 }
                            Label { text: Trades; Layout.preferredWidth: 80 }
                            Label { text: Universe; Layout.preferredWidth: 60 }
                            Label { text: Folds; Layout.preferredWidth: 60 }
                        }
                    }
                }
            }
        }

        // --- Live (placeholder) ---
        Item {
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                Label { text: "כאן נכנסת לשונית ה-Live הקיימת שלך"; }
            }
        }

        // --- Help ---
        Item {
            ScrollView {
                anchors.fill: parent; anchors.margins: 16
                Column {
                    width: parent.width
                    spacing: 8
                    Label { text: "עזרה"; font.pixelSize: 18; font.bold: true }
                    Label { text: "Optimize: בחר טווחי פרמטרים (JSON), גודל יקום, Walk-Forward, ויעד דירוג. התוצאות ממוינות לפי Score." }
                }
            }
        }
    }

    FileDialog {
        id: folderDlg
        title: "בחר תיקייה"
        selectFolder: true
        onAccepted: {
            var p = fileUrl.toLocalFile ? fileUrl.toLocalFile() : fileUrl.toString()
            win.dataDir = p
        }
    }

    Connections {
        target: controller
        function onStatusChanged(msg) { console.log(msg) }
    }
}
