<#
.SYNOPSIS
    Run Datera PoC checks to determine fitness for communicating with a Datera cluster
.DESCRIPTION
    This script will run through the following checks to determine if it is ready
    for use with a Datera cluster.
        * ISCSI services check
        * Management connection check
        * VIP1 connection check
        * VIP2 connection check
        * Management mtu check
        * VIP1 mtu check
        * VIP2 mtu check
        * Power settings check
        * Receive side scaling check
.EXAMPLE
    Copy this file to the Desktop of the Admin account
    Run
    C:\Users\Admin\Desktop\check_windows.ps1 172.19.1.41 172.28.222.9 172.29.222.9-human
    --------------
    Example Output
    --------------
    Checking ISCSI Service
    SUCCESS
    Testing vip_1 Connection
    SUCCESS
    Testing vip_2 Connection
    SUCCESS
    Testing mgmt_ip Connection
    SUCCESS
    vip_2 was not populated, skipping MTU test
    Testing vip_1 MTU
    SUCCESS
    Testing mgmt_ip MTU
    SUCCESS
    Checking Power Settings
    Power settings are not set to 'High performance'
    Checking Recieve Side Scaling
    SUCCESS
    Finished.  Status Code: 256
    FAILED_POWER_SETTINGS

    Each check will either report SUCCESS or it will display an error at the end
    of the test run.
#>

Param(
    [Parameter(Mandatory=$true)]
    [string]$mgmt,

    [Parameter(Mandatory=$true)]
    [string]$vip_1,

    [Parameter(Mandatory=$false)]
    [string]$vip_2 = "",

    [Parameter(Mandatory=$false)]
    [switch]$human = $false
)


Set-StrictMode -Version Latest

$conf = @{"mgmt_ip" = $mgmt; "vip_1" = $vip_1; "vip_2" = $vip_2}
$EXITCODE = 0

$FAILED_ISCSI_SERVICE   = 2
$FAILED_CONNECTION_MGMT = 4
$FAILED_CONNECTION_VIP1 = 8
$FAILED_CONNECTION_VIP2 = 16
$FAILED_MTU_MGMT        = 32
$FAILED_MTU_VIP1        = 64
$FAILED_MTU_VIP2        = 128
$FAILED_POWER_SETTINGS  = 256
$FAILED_RSS             = 512

$human_readable = @{
    $FAILED_ISCSI_SERVICE   =  "FAILED_ISCSI_SERVICE";
    $FAILED_CONNECTION_MGMT =  "FAILED_CONNECTION_MGMT";
    $FAILED_CONNECTION_VIP1 =  "FAILED_CONNECTION_VIP1";
    $FAILED_CONNECTION_VIP2 =  "FAILED_CONNECTION_VIP2";
    $FAILED_MTU_MGMT        =  "FAILED_MTU_MGMT";
    $FAILED_MTU_VIP1        =  "FAILED_MTU_VIP1";
    $FAILED_MTU_VIP2        =  "FAILED_MTU_VIP2";
    $FAILED_POWER_SETTINGS  =  "FAILED_POWER_SETTINGS";
    $FAILED_RSS             =  "FAILED_RSS"
}

function Add-Error {
    Param([Parameter(Mandatory=$true)] [int]$error_code)
    $script:EXITCODE += $error_code
}

function Write-Human {
    Param([Parameter(Mandatory=$true)] [string]$output)
    If ($human) {
        Write-Output $output
    }
}

# Check ISCSI service
Write-Human "Checking ISCSI Service"
$iscsi_enabled = (Get-Service MSiSCSI).Status -eq "Running"
If (!$iscsi_enabled) {
    Write-Human "FAIL: The MSiSCSI service is not running"
    Add-Error $FAILED_ISCSI_SERVICE
} Else {
    Write-Human "SUCCESS"
}

# Check Connections
$conn_errs = @{"mgmt_ip" = $FAILED_CONNECTION_MGMT;
               "vip_1" = $FAILED_CONNECTION_VIP1;
               "vip_2" = $FAILED_CONNECTION_VIP2}
Foreach ($k in $conf.keys) {
    If ($conf[$k] -eq "") {
        Write-Human "$k was not populated, skipping connection test"
        continue
    }
    Write-Human "Testing $k Connection"
    If (!(Test-Connection -Cn $conf[$k] -BufferSize 16 -Count 1 -ea 0 -quiet)) {
        Write-Human "FAIL: Could not reach $conf[$k], please check the connection"
        Add-Error $conn_errs[$k]
    } Else {
        Write-Human "SUCCESS"
    }
}

# Check MTU
$mtu = 9000
$mtu_errs = @{"mgmt_ip" = $FAILED_MTU_MGMT;
              "vip_1" = $FAILED_MTU_VIP1;
              "vip_2" = $FAILED_MTU_VIP2}
Foreach ($k in $conf.keys) {
    If ($conf[$k] -eq "") {
        Write-Human "$k was not populated, skipping MTU test"
        continue
    }
    Write-Human "Testing $k MTU"
    If (!(ping $conf[$k] -f -l $mtu)) {
        Write-Human "Could not reach $conf[$k], with MTU of $mtu, please check MTU settings"
        Add-Error $mtu_errs[$k]
    } Else {
        Write-Human "SUCCESS"
    }
}

# Check Power Settings
Write-Human "Checking Power Settings"
If (!(powercfg -l | Where-Object {$_.contains("High performance")} | Foreach-Object {$_.contains("*")})) {
    Write-Human("Power settings are not set to 'High performance'")
    Add-Error $FAILED_POWER_SETTINGS
}

# Check Receive Side Scaling
Write-Human "Checking Recieve Side Scaling"
$rssm = Get-NetAdapterRss * | Where-Object {$_.Enabled -eq $false} | Measure-Object
If ($rssm.Count -ne 0) {
    Get-NetAdapterRss * | Where-Object {$_.Enabled -eq $false} | Foreach-Object {
            Write-Human "Interface $_.Name does not have Receive Side Scaling enabled"
        }
    Add-Error $FAILED_RSS
} Else {
    Write-Human "SUCCESS"
}

Write-Human("Finished.  Status Code: $EXITCODE")
if ($human) {
    $human_readable.Keys | Where-Object {$_ -band $EXITCODE} | Foreach-Object {Write-Human $human_readable[$_]}
}
exit $EXITCODE
