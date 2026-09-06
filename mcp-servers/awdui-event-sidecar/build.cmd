@echo off
dotnet publish -c Release -r win-x64 --self-contained false -o publish
echo Event sidecar built to publish\awdui-event-sidecar.exe
