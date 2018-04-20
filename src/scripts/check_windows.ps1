Param(
    [Parameter(Mandatory=$true)]
    [string]$mgmt,

    [Parameter(Mandatory=$true)]
    [string]$vip_1,

    [Parameter(Mandatory=$false)]
    [string]$vip_2 = ""
)

Set-StrictMode -Version Latest

$conf = @{"mgmt_ip" = $mgmt; "vip_1" = $vip_1; "vip_2" = $vip_2}
$EXITCODE = 0

$FAILED_ISCSI_SERVICE = 2
$FAILED_CONNECTION_MGMT = 4
$FAILED_CONNECTION_VIP1 = 8
$FAILED_CONNECTION_VIP2 = 16
$FAILED_MTU_MGMT = 32
$FAILED_MTU_VIP1 = 64
$FAILED_MTU_VIP2 = 128
$FAILED_POWER_SETTINGS = 256
$FAILED_RSS = 512

function Add-Error {
    Param([Parameter(Mandatory=$true)] [int]$error_code)
    $script:EXITCODE += $error_code
}

# Check ISCSI service
Write-Output "Checking ISCSI Service"
$iscsi_enabled = (Get-Service MSiSCSI).Status -eq "Running"
If (!$iscsi_enabled) {
    Write-Output "The MSiSCSI service is not running"
    Add-Error $FAILED_ISCSI_SERVICE
}

# Check Connections
$conn_errs = @{"mgmt_ip" = $FAILED_CONNECTION_MGMT;
               "vip_1" = $FAILED_CONNECTION_VIP1;
               "vip_2" = $FAILED_CONNECTION_VIP2}
Foreach ($k in $conf.keys) {
    If ($conf[$k] -eq "") {
        Write-Output "$k was not populated, skipping connection test"
        continue
    }
    Write-Output "Testing $k"
    If (!(Test-Connection -Cn $conf[$k] -BufferSize 16 -Count 1 -ea 0 -quiet)) {
        Write-Output "Could not reach $conf[$k], please check the connection"
        Add-Error $conn_errs[$k]
    }
}

# Check MTU
$mtu = 9000
$mtu_errs = @{"mgmt_ip" = $FAILED_MTU_MGMT;
              "vip_1" = $FAILED_MTU_VIP1;
              "vip_2" = $FAILED_MTU_VIP2}
Foreach ($k in $conf.keys) {
    If ($conf[$k] -eq "") {
        Write-Output "$k was not populated, skipping MTU test"
        continue
    }
    Write-Output "Testing $k"
    If (!(ping $conf[$k] -f -l $mtu)) {
        Write-Output "Could not reach $conf[$k], with MTU of $mtu, please check MTU settings"
        Add-Error $mtu_errs[$k]
    }
}

# Check Power Settings
If (!(powercfg -l | Where-Object {$_.contains("High performance")} | Foreach-Object {$_.contains("*")})) {
    Write-Output("Power settings are not set to 'High performance'")
    Add-Error $FAILED_POWER_SETTINGS
}

# Check Receive Side Scaling
$rssm = Get-NetAdapterRss * | Where-Object {$_.Enabled -eq $false} | Measure-Object
If ($rssm -ne 0) {
    Write-Output("Detected one or more interfaces without Receive Side Scaling enabled")
    Get-NetAdapterRss * | Where-Object {$_.Enabled -eq $false} | Foreach-Object {Write-Output $_.Name}
    Add-Error $FAILED_RSS
}

Write-Output("Finished.  Status Code: $EXITCODE")
exit $EXITCODE
